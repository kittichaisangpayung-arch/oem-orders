import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from apps.core.models import Customer, Store


@pytest.mark.django_db
def test_staff_can_list_create_update_delete_store():
    staff = User.objects.create_user(username="staffuser", password="testpass123", is_staff=True)
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")

    client = Client()
    client.force_login(staff)

    response = client.get(reverse("manage_data:store_list"))
    assert response.status_code == 200

    response = client.post(
        reverse("manage_data:store_add"),
        {"customer": customer.pk, "store_code": "S1", "name": "New Store", "is_active": "on"},
    )
    assert response.status_code == 302
    store = Store.objects.get(store_code="S1")
    assert store.name == "New Store"

    response = client.post(
        reverse("manage_data:store_edit", args=[store.pk]),
        {"customer": customer.pk, "store_code": "S1", "name": "Renamed Store", "is_active": "on"},
    )
    assert response.status_code == 302
    store.refresh_from_db()
    assert store.name == "Renamed Store"

    response = client.post(reverse("manage_data:store_delete", args=[store.pk]))
    assert response.status_code == 302
    assert not Store.objects.filter(pk=store.pk).exists()


@pytest.mark.django_db
def test_non_staff_blocked_from_all_crud_actions():
    user = User.objects.create_user(username="regular", password="testpass123")
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    store = Store.objects.create(customer=customer, store_code="S1", name="Store 1")

    client = Client()
    client.force_login(user)

    assert client.get(reverse("manage_data:store_list")).status_code == 403
    assert client.get(reverse("manage_data:store_add")).status_code == 403
    assert client.get(reverse("manage_data:store_edit", args=[store.pk])).status_code == 403
    assert client.get(reverse("manage_data:store_delete", args=[store.pk])).status_code == 403

    assert Store.objects.filter(pk=store.pk).exists()


@pytest.mark.django_db
def test_deleting_customer_cascades_to_its_stores():
    staff = User.objects.create_user(username="staffuser2", password="testpass123", is_staff=True)
    customer = Customer.objects.create(name="Donki", code="DONKI", parser_key="donki_v1")
    store = Store.objects.create(customer=customer, store_code="S1", name="Store 1")

    client = Client()
    client.force_login(staff)

    response = client.post(reverse("manage_data:customer_delete", args=[customer.pk]))
    assert response.status_code == 302

    assert not Customer.objects.filter(pk=customer.pk).exists()
    assert not Store.objects.filter(pk=store.pk).exists()
