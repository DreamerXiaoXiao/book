from drf_haystack.viewsets import HaystackViewSet
from rest_framework import status
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView, GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_extensions.cache.mixins import CacheResponseMixin

from .models import SKU, Category, Channel, KeyWord
from . import serializers
from .utils import get_categories
from . import constants


class SKUListView(ListAPIView):
    """
    查询三级分类下的所有商品
    """
    serializer_class = serializers.SKUSerializer

    # 过滤
    filter_backends = (OrderingFilter,)
    ordering_fields = ('create_time', 'price', 'sales')

    # 分页统一设置

    def get_queryset(self):
        category_id = self.kwargs['category_id']
        return SKU.objects.filter(category_id=category_id, is_launched=True)


class GoodsCategoryListView(CacheResponseMixin, GenericAPIView):

    def get(self, request):
        return Response(get_categories())


class HotSKUListView(ListAPIView):
    serializer_class = serializers.SKUSerializer
    pagination_class = None
    # 分页统一设置

    def get_queryset(self):
        category_id = self.kwargs['category_id']
        return SKU.objects.filter(category_id=category_id, is_launched=True).order_by('-sales')[0: constants.HOT_GOODS_MAX_LIMIT]


class BreadcrumbView(APIView):
    """面包屑导航栏"""
    def get(self, request, category_id):

        context = {}
        try:
            cat3 = Category.objects.get(id=category_id)

            context['cat3'] = {'name': cat3.name}
            cat2 = Category.objects.get(id=cat3.parent_id)
            context['cat2'] = {'name': cat2.name}
            cat1 = Category.objects.get(id=cat2.parent_id)
            gc = Channel.objects.get(category_id=cat1.id)
        except Exception as e:
            return Response('分类不存在', status=status.HTTP_400_BAD_REQUEST)
        else:
            context['cat1'] = {
                'url': gc.url,
                'category': {'name': cat1.name }
            }
            return Response(context)


class KeyWordView(ListAPIView):
    serializer_class = serializers.KeyWordSerializer
    pagination_class = None
    queryset = KeyWord.objects.all()[0:constants.KEY_WORD_MAX_LIMIT]


class SKUSearchViewSet(HaystackViewSet):
    """
    SKU搜索
    """
    index_models = [SKU]
    serializer_class = serializers.SKUIndexSerializer


from . import models


class AddDataView(APIView):

    def get(self, request):
        from pymongo import MongoClient

        client = MongoClient(host='127.0.0.1')
        collection = client['JD']['book']
        books = collection.find()
        for book in books:
            print(book['b_cate'], book['s_cate'])
            try:
                book_author = ' '.join(book['book_author'])
            except Exception as e:
                pass
            # try:
            #     cat2 = models.Category.objects.get(name=book['b_cate'])
            # except Exception as e:
            #     cat2 = models.Category.objects.create(
            #         name=book['b_cate']
            #     )
            # try:
            #     cat3 = models.Category.objects.get(name=book['s_cate'])
            # except Exception as e:
            #     cat3 = models.Category.objects.create(
            #         name=book['s_cate']
            #     )
            # cat3.parent = cat2
            # cat3.save()


            cat = models.Category.objects.get(name=book['s_cate'])
            try:
                sku = models.SKU.objects.get(name=book['book_title'])
                sku.desc_service = book['book_service']
                sku.save()
            except Exception as e:
                models.SKU.objects.create(
                    name=book['book_title'],
                    category=cat,
                    price=book['book_price'],
                    cost_price=float(book['book_price']) * 0.8,
                    market_price=float(book['book_price']) * 1.3,
                    default_image_url=book['book_img'],
                    author=book_author,
                    stock=10,
                    desc_detail=book['book_detail'],
                )
        return Response('ok')

