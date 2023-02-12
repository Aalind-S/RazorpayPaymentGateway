from django.shortcuts import render
import razorpay
import json
from .constants import PaymentStatus
from django.views.decorators.csrf import csrf_exempt
from portal.models import Order
from RazorPayment.settings import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET
# Create your views here.


def home(request):
    return render(request, "index.html")


def order_payment(request):
    if request.method == "POST":
        name = request.POST.get("name")
        amount = request.POST.get("amount")
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

        DATA = {
            "amount": int(amount)*100,
            "currency": "INR",
            "payment_capture": "1",
        }
        razorpay_order = client.order.create(data=DATA)
        order = Order.objects.create(name=name, amount=amount, order_id=razorpay_order["id"])
        order.save()

        """
            this is created when the order is created (razorpay_order)
            {
              "id": "order_IX37nLMvHfLsSO",
              "entity": "order",
              "amount": 789600,
              "amount_paid": 0,
              "amount_due": 789600,
              "currency": "INR",
              "receipt": null,
              "offer_id": null,
              "status": "created",
              "attempts": 0,
              "notes": [],
              "created_at": 1639418188
              }

            """
        return render(request, 'payment.html',
                      {
                          "callback_url": "http://" + "127.0.0.1:8000" + "/razorpay/callback/",
                          "razorpay_key": "rzp_test_BBx5TcJL1kgzp9",
                          "order": order

                      }
                      )

    return render(request, 'payment.html')


@csrf_exempt
def callback(request):
    def verify_signature(response_data):
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        return client.utility.verify_payment_signature(response_data)

    if "razorpay_signature" in request.POST:
        payment_id = request.POST.get("razorpay_payment_id", "")
        order_id = request.POST.get("razorpay_order_id", "")
        signature_id = request.POST.get("razorpay_signature", "")
        order = Order.objects.get(order_id=order_id)
        order.payment_id = payment_id
        order.signature_id = signature_id
        order.save()
        if not verify_signature(request.POST):
            order.status = PaymentStatus.FAILURE
            order.save()
            return render(request, "callback.html", context={"status": order.status})
        else:
            order.status = PaymentStatus.SUCCESS
            order.save()
            return render(request, "callback.html", context={"status": order.status})
    else:
        payment_id = json.loads(request.POST.get("error[metadata]")).get("payment_id")
        order_id = json.loads(request.POST.get("error[metadata]")).get("order_id")
        order = Order.objects.get(order_id=order_id)
        order.payment_id = payment_id
        order.status = PaymentStatus.FAILURE
        order.save()
        return render(request, "callback.html", context={"status": order.status})
