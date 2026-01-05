from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.http import JsonResponse
from .models import Doctor

#Payment Views
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest

def home(request):
    doctors = Doctor.objects.all()
    return render(request, 'core/home.html', {'doctors': doctors})

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the user in immediately after signing up
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'core/signup.html', {'form': form})

def register(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        specialty = request.POST.get('specialty')
        Doctor.objects.create(name=name, specialty=specialty)
        return redirect('home')
    return render(request, 'core/register.html')

# AJAX Delete Operation
def delete_doctor(request):
    id = request.GET.get('id')
    Doctor.objects.get(id=id).delete()
    return JsonResponse({'deleted': True})

# Payment Integration Views
# Replace with your keys from Razorpay Dashboard -> Settings -> API Keys
RAZORPAY_KEY_ID = 'rzp_test_S0GRrXzzyiT3Nq'
RAZORPAY_KEY_SECRET = 'HcE5ibSBV07G9tzQjygteXSK'

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def initiate_payment(request):
    currency = 'INR'
    amount = 50000  # Amount is in currency subunits (50000 Paise = 500 INR)

    # 1. Create a Razorpay Order
    razorpay_order = client.order.create({
        "amount": amount,
        "currency": currency,
        "payment_capture": "1" # Auto-capture payment
    })

    # 2. Pass the order ID and keys to the template
    context = {
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_merchant_key': RAZORPAY_KEY_ID,
        'razorpay_amount': amount,
        'currency': currency,
        'callback_url': "http://127.0.0.1:8000/payment-status/", # Update for PythonAnywhere
    }

    return render(request, 'core/razorpay_checkout.html', context=context)

@csrf_exempt
def payment_status(request):
    # Razorpay sends payment_id, order_id, and signature to verify
    if request.method == "POST":
        try:
            params_dict = {
                'razorpay_order_id': request.POST.get('razorpay_order_id'),
                'razorpay_payment_id': request.POST.get('razorpay_payment_id'),
                'razorpay_signature': request.POST.get('razorpay_signature')
            }

            # VERIFY THE SIGNATURE
            res = client.utility.verify_payment_signature(params_dict)
            if res is None: # Signature matches
                return render(request, 'core/payment_status.html', {'status': 'Success'})
        except:
            return render(request, 'core/payment_status.html', {'status': 'Failed'})
    return HttpResponseBadRequest()