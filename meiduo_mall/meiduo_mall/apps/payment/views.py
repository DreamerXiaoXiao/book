import os
from alipay import AliPay
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from orders.models import OrderInfo
from payment.models import Payment


class PaymentView(APIView):
    """
        支付
        """
    permission_classes = (IsAuthenticated,)

    def get(self, request, order_id):
        """
        获取支付链接
        """
        # 判断订单信息是否正确
        try:
            order = OrderInfo.objects.get(
                order_id=order_id,
                user=request.user,
                pay_method=OrderInfo.PAY_METHODS_ENUM['ALIPAY'],
                status=OrderInfo.ORDER_STATUS_ENUM['UNPAID']
            )
        except OrderInfo.DoesNotExist:
            return Response({'message': '订单信息有误'}, status=status.HTTP_400_BAD_REQUEST)
        # 构造支付宝支付链接地址
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'keys/app_private_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'keys/alipay_public_key.pem'),
            sign_type="RSA2",  # RSA 或者 RSA2
            debug = settings.ALIPAY_DEBUG  # 默认False
        )

        # 电脑网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(order.total_amount),
            subject='订单编号:%s' % order_id,
            return_url=settings.ALIPY_SUCCESS,
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        # 拼接付链接返回前端
        alipay_url = settings.ALIPAY_URL + order_string
        return Response({'alipay_url': alipay_url})


class PaymentStatusView(APIView):
    """
    支付结果
    """
    permission_classes = [IsAuthenticated]

    def put(self, request):

        # req_data = request.query_params 为QueryDict
        # req_dict = req_data.dict()      为dict
        data = request.query_params.dict()
        signature = data.pop("sign")

        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/app_private_key.pem"),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "keys/alipay_public_key.pem"),  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=settings.ALIPAY_DEBUG  # 默认False
        )

        success = alipay.verify(data, signature)
        if success:
            # 订单编号
            order_id = data.get('out_trade_no')
            # 支付宝支付流水号
            trade_id = data.get('trade_no')
            Payment.objects.create(
                order_id=order_id,
                trade_id=trade_id
            )
            OrderInfo.objects.filter(order_id=order_id, status=OrderInfo.ORDER_STATUS_ENUM['UNPAID']).update(status=OrderInfo.ORDER_STATUS_ENUM["UNRECEIVED"])
            return Response({'trade_id': trade_id})
        else:
            return Response({'message': '非法请求'}, status=status.HTTP_403_FORBIDDEN)