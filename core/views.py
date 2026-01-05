from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required # New Import
from django.http import JsonResponse, HttpResponseBadRequest
from .models import Doctor

# Payment Views
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

# --- Razorpay Configuration ---
# Recommendation: Move these to settings.py or environment variables later
RAZORPAY_KEY_ID = 'rzp_test_S0GRrXzzyiT3Nq'
RAZORPAY_KEY_SECRET = 'HcE5ibSBV07G9tzQjygteXSK'

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def home(request):
    doctors = Doctor.objects.all()
    return render(request, 'core/home.html', {'doctors': doctors})

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'core/signup.html', {'form': form})

@login_required # Only logged-in users can register doctors
def register(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        specialty = request.POST.get('specialty')
        Doctor.objects.create(name=name, specialty=specialty)
        return redirect('home')
    return render(request, 'core/register.html')

@login_required # Only logged-in users can delete
def delete_doctor(request):
    id = request.GET.get('id')
    try:
        Doctor.objects.get(id=id).delete()
        return JsonResponse({'deleted': True})
    except Doctor.DoesNotExist:
        return JsonResponse({'deleted': False}, status=404)

# --- Payment Integration Views ---

@login_required # Users MUST be logged in to pay
def initiate_payment(request):
    currency = 'INR'
    amount = 50000  # 500 INR

    # 1. Create a Razorpay Order
    razorpay_order = client.order.create({
        "amount": amount,
        "currency": currency,
        "payment_capture": "1" 
    })

    # 2. Dynamic Callback URL
    # This automatically detects if you are on localhost or PythonAnywhere
    domain = request.get_host()
    protocol = 'https' if request.is_secure() else 'http'
    callback_url = f"{protocol}://{domain}/payment-status/"

    context = {
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_merchant_key': RAZORPAY_KEY_ID,
        'razorpay_amount': amount,
        'currency': currency,
        'callback_url': callback_url, 
    }

    return render(request, 'core/razorpay_checkout.html', context=context)

@csrf_exempt
def payment_status(request):
    if request.method == "POST":
        try:
            params_dict = {
                'razorpay_order_id': request.POST.get('razorpay_order_id'),
                'razorpay_payment_id': request.POST.get('razorpay_payment_id'),
                'razorpay_signature': request.POST.get('razorpay_signature')
            }

            # VERIFY THE SIGNATURE
            res = client.utility.verify_payment_signature(params_dict)
            
            # Razorpay's verify_payment_signature returns None if successful, 
            # or raises an error if it fails.
            return render(request, 'core/payment_status.html', {'status': 'Success'})
        except Exception as e:
            return render(request, 'core/payment_status.html', {'status': 'Failed'})
            
    return HttpResponseBadRequest()