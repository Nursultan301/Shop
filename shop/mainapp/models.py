import sys
from PIL import Image
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadhandler import InMemoryUploadedFile


from io import BytesIO

User = get_user_model()


def get_models_for_count(*model_names):
    return [models.Count(model_name) for model_name in model_names]


def get_product_url(obj, viewname):
    ct_model = obj.__class__._meta.model_name
    return reverse(viewname, kwargs={'ct_model': ct_model, 'slug': obj.slug})


class MinResolutionErrorException(Exception):
    pass


class MaxResolutionErrorException(Exception):
    pass


class LatestProductsManager:

    def get_products_for_main_page(*args, **kwargs):
        with_products_to = kwargs.get('with_products_to')
        products = []
        ct_models = ContentType.objects.filter(model__in=args)
        for ct_model in ct_models:
            model_products = ct_model.model_class()._base_manager.all().order_by('-id')[:5]
            products.extend(model_products)
        if with_products_to:
            ct_model = ContentType.objects.filter(model=with_products_to)
            if ct_model.exists():
                if with_products_to in args:
                    return sorted(products, key=lambda x: x.__class__._meta.model_name.startswith(with_products_to),
                                  reverse=True)
        return products


class LatestProducts:

    objects = LatestProductsManager()


class CategoryManager(models.Manager):

    CATEGORY_NAME_COUNT_NAME = {
        'Ноутбуки': "notebook__count",
        'Смартфоны': 'smartphone__count'

    }

    def get_queryset(self):
        return super().get_queryset()

    def get_categories_for_left_sidebar(self):
        models = get_models_for_count('notebook', 'smartphone')
        qs = list(self.get_queryset().annotate(*models))
        date =[
            dict(name=c.name, url=c.get_absolute_url(), count=getattr(c, self.CATEGORY_NAME_COUNT_NAME[c.name]))
            for c in qs
        ]
        return date


class Category(models.Model):
    """ Категория """
    name = models.CharField('Имя категории', max_length=255)
    slug = models.SlugField('Url', unique=True)
    objects = CategoryManager()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category_detail', kwargs={'slug': self.slug})

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = 'Категории'


class Product(models.Model):
    """ Товар """

    MIN_RESOLUTION = (200, 200)
    MAX_RESOLUTION = (800, 800)
    MAX_IMAGE_SIZE = 3145728

    title = models.CharField('Наименование', max_length=255)
    description = models.TextField('Описание', null=True)
    slug = models.SlugField("Url", unique=True)
    image = models.ImageField('Изображение')
    price = models.DecimalField('Цена', max_digits=9, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='Категория')

    def __str__(self):
        return self.title

    def get_model_name(self):
        return self.__class__.__name__.lower()

    def save(self, *args, **kwargs):
        image = self.image
        img = Image.open(image)
        min_height, min_width = self.MIN_RESOLUTION
        max_height, max_width = self.MAX_RESOLUTION
        if img.height < min_height or img.width < min_width:
            raise MinResolutionErrorException('Разрешение изображения меньше минимального!')
        if img.height < max_height or img.width < max_width:
            raise MaxResolutionErrorException('Разрешение изображения больше максимального!')
        print(img.width, img.height)
        # image = self.image
        # img = Image.open(image)
        # new_img = img.convert('RGB')
        # resized_new_img = new_img.resize((200, 200), Image.ANTIALIAS)
        # filestream = BytesIO()
        # resized_new_img.save(filestream, 'JPEG', quality=90)
        # filestream.seek(0)
        # name = '{}.{}'.format(*self.image.name.split('.'))
        # self.image = InMemoryUploadedFile(
        #     filestream, 'ImageField', name, 'jpeg/image', sys.getsizeof(filestream), None
        # )
        # super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = 'Товары'
        abstract = True


class Notebook(Product):
    """ Ноутбук """
    diagonal = models.CharField('Диагональ', max_length=255)
    display_type = models.CharField('Тип дисплея', max_length=255)
    processor_freq = models.CharField('Чистота процессора', max_length=255)
    ram = models.CharField('Опаративная память', max_length=255)
    video = models.CharField('Видеокарта', max_length=255)
    time_without_charge = models.CharField('Время работы аккумулятора', max_length=255)

    def __str__(self):
        return "{} : {}".format(self.category.name, self.title)

    def get_absolute_url(self):
        return get_product_url(self, 'product_detail')

    class Meta:
        verbose_name = "Ноутбук"
        verbose_name_plural = 'Ноутбуки'


class Smartphone(Product):
    """ Смартфон """
    diagonal = models.CharField('Диагональ', max_length=255)
    display_type = models.CharField('Тип дисплея', max_length=255)
    resolution = models.CharField('Разрешение экрана', max_length=255)
    accum_volume = models.CharField('Объем батереи', max_length=255)
    ram = models.CharField('Опаративная память', max_length=255)
    sd = models.BooleanField('Наличие SD карты', default=True)
    sd_volume_max = models.CharField('Максимальный объем встраивамой памяти', null=True, blank=True,  max_length=255)
    main_cam_mp = models.CharField('Главная камера', max_length=255)
    frontal_cam_mp = models.CharField('Фронтальная камера', max_length=255)

    def get_absolute_url(self):
        return get_product_url(self, 'product_detail')

    @property
    def sd_v(self):
        return 'Да' if self.sd else 'Нет'

    def __str__(self):
        return "{} : {}".format(self.category.name, self.title)

    class Meta:
        verbose_name = "Телефон"
        verbose_name_plural = 'Телефоны'


class CartProduct(models.Model):
    """Товар в корзине"""
    user = models.ForeignKey('Customer', on_delete=models.CASCADE, verbose_name="Покупатель")
    cart = models.ForeignKey('Cart', on_delete=models.CASCADE, verbose_name='Корзина', related_name='related_products')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    qty = models.PositiveIntegerField('Количество', default=1)
    final_price = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Общая цена')

    def __str__(self):
        return "Продукт: {} (для корзины)".format(self.content_object.title)

    def save(self, *args, **kwargs):
        self.final_price = self.qty * self.content_object.price
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Товар в корзине"
        verbose_name_plural = 'Товар в корзине'


class Cart(models.Model):
    """ Корзина """
    owner = models.ForeignKey('Customer', null=True, on_delete=models.CASCADE, verbose_name='Владелец')
    products = models.ManyToManyField(CartProduct, blank=True, related_name='related_card')
    total_products = models.PositiveIntegerField(default=0)
    final_price = models.DecimalField(max_digits=9, default=0, decimal_places=2, verbose_name='Общая цена')
    in_order = models.BooleanField(default=False)
    for_anonymous_user = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = 'Корзина'


class Customer(models.Model):
    """ Покупатель """
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    phone = models.CharField('Номер телефона', max_length=20, null=True, blank=True)
    address = models.CharField('Адрес', max_length=255, null=True, blank=True)
    orders = models.ManyToManyField("Order", verbose_name='Заказы покупателя', related_name='related_customer')

    def __str__(self):
        return "Покупатель: {} {}".format(self.user.first_name, self.user.last_name)

    class Meta:
        verbose_name = "Покупатель"
        verbose_name_plural = 'Покупатели'


class Order(models.Model):

    STATUS_NEW = 'new'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_READY = 'is_ready'
    STATUS_COMPLETED = 'completed'

    BUYING_TYPE_SELF = 'self'
    BUYING_TYPE_DELIVERY = 'delivery'

    STATUS_CHOICES = (
        (STATUS_NEW, 'Новый заказ'),
        (STATUS_IN_PROGRESS, 'Заказ в отработке'),
        (STATUS_READY, 'Заказ готов'),
        (STATUS_COMPLETED, 'Заказ выполнен'),
    )

    BUYING_TYPE_CHOICES = (
        (BUYING_TYPE_SELF, 'Самовывоз'),
        (BUYING_TYPE_DELIVERY, 'Доставка')
    )

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='related_orders', verbose_name='Покупатель')
    first_name = models.CharField(max_length=255, verbose_name='Имя')
    last_name = models.CharField(max_length=255, verbose_name='Фамилия')
    phone = models.CharField(max_length=12, verbose_name='Телефон')
    cart = models.ForeignKey(Cart, verbose_name='Корзина', on_delete=models.CASCADE, null=True, blank=True)
    address = models.CharField(max_length=255, verbose_name='Адрес', null=True, blank=True)
    status = models.CharField(
        max_length=100,
        verbose_name='Статус заказа',
        choices=STATUS_CHOICES,
        default=STATUS_NEW
    )
    buying_type = models.CharField(
        max_length=100,
        verbose_name='Тип заказа',
        choices=BUYING_TYPE_CHOICES,
        default=BUYING_TYPE_SELF
    )
    comment = models.TextField('Комментарий к заказу', null=True, blank=True)
    created_at = models.DateTimeField('Дата создания заказа', auto_now=True)
    order_date = models.DateField(verbose_name='Дата получение заказа', default=timezone.now)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

