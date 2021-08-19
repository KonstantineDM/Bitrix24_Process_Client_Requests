import os
from datetime import datetime

import dotenv
from fast_bitrix24 import Bitrix

dotenv.load_dotenv()

# Входящий вебхук, созданный на портале Битрикс24
webhook = os.environ.get("WEBHOOK")
# Объект Битрикс для доступа к Битрикс24
b = Bitrix(webhook)


def get_deal_fields():
    """
    Возвращает описание полей сделки, в том числе пользовательских;
    Пользовательские поля названы по шаблону "UF_CRM_1629120722137"
    rtype: dict
    """
    deal_fields = b.get_all(
        "crm.deal.fields"
    )
    return deal_fields


def add_deal_userfields(field_names, deal_fields):
    """
    Проверяет наличие необходимых полей в форме сделки;
    создает необходимые поля в случае их отсутствия;
    returns : None
    rtype   : None
    """
    sort = 100  # Параметр "Сортировка" для первого пользовательского поля
    for field_name in field_names:
        # Проверяем, есть ли нужные нам поля на портале
        if ("UF_CRM_" + field_name.upper()) not in list(deal_fields):
            # Создаем нужные поля
            try:
                task = {
                    "fields": {
                        "FIELD_NAME": field_name,
                        "EDIT_FORM_LABEL": field_names[field_name],
                        "LIST_COLUMN_LABEL": field_names[field_name],
                        "USER_TYPE_ID": "string",
                        # "MANDATORY": "Y", 
                        "SHOW_IN_LIST": "Y", 
                        "SORT": sort,
                    }
                }
                b.call(
                    "crm.deal.userfield.add", task
                )
                print(f'Поле {task["fields"]["FIELD_NAME"]} создано.')
            except RuntimeError:
                print(f"Ошибка. Возможно поле {field_name} уже существует.")
            sort += 100     # Для каждого нового поля увеличивается на 100


def generate_b24_data(query_data):
    """
    Получает заявку query_data в виде JSON с сайта;
    формирует из заявки два словаря:
    1. crm.deal - сведения о Сделке;
    2. crm.contact - сведения о Контакте;
    returns : payload - словарь, содержащий crm.deal и crm.contact
    rtype   : dict
    """
    payload = {
        "crm.deal": {
        "deal_title": query_data["title"],
        "deal_description": query_data["description"],
        "deal_products": query_data["products"],
        "deal_delivery_adress": query_data["delivery_adress"],
        "deal_delivery_date": query_data["delivery_date"],
        "deal_delivery_code": query_data["delivery_code"],
        },
        "crm.contact": {
        "contact_name": query_data["client"]["name"],
        "contact_surname": query_data["client"]["surname"],
        "contact_phone": query_data["client"]["phone"],
        "contact_adress": query_data["client"]["adress"]
        }
    }
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Поступила заявка:")
    print(payload)
    return payload


def get_contact_list():
    # Возвращает список контактов по фильтру
    # rtype: list[dict]
    contact_list = b.get_all(
        "crm.contact.list",
        params={'select': ["ID", 
                           "NAME", 
                           "LAST_NAME", 
                           "PHONE",
                           "EMAIL",
                           "TYPE_ID",
                           "ADDRESS",
                           "ADDRESS_2",
                           "SOURCE_ID" ]}
    )
    return contact_list


def contact_add_update(contact_list, payload):
    """
    Проверяет наличие на портале Битрикс24 контакта, указанного в заявке;
    создаёт новый контакт, если таковой на портале отсутствует, 
    или обновляет существующий контакт новыми данными (тел.номер)
    returns : contact_id - номер созданного/обновленного контакта
    rtype   : str
    """
    match_id = []   # Если контакт существует, добавляет его ID для дальнейшего обновления
    for contact in contact_list:
        if [
            payload["crm.contact"]["contact_name"], 
            payload["crm.contact"]["contact_surname"], 
            payload["crm.contact"]["contact_adress"]
            ] == [
            contact["NAME"],
            contact["LAST_NAME"],
            contact["ADDRESS"]
            ]:
            print("Контакт уже существует.")
            match_id.append(contact["ID"])
    if not match_id:
        print("Создаю новый контакт.")
        b.call(
            "crm.contact.add", {
                "fields": {
                    "NAME": payload["crm.contact"]["contact_name"],
                    "LAST_NAME": payload["crm.contact"]["contact_surname"],
                    "TYPE_ID": "CLIENT",
                    "SOURCE_ID": "SELF",
                    "PHONE": [{"VALUE": payload["crm.contact"]["contact_phone"]}],
                    "ADDRESS": payload["crm.contact"]["contact_adress"],
                    
                }
            }
        )
        # Если создается новый контакт, то его ID будет в последнем словаре списка контактов
        contact_id = get_contact_list()[-1]["ID"]
    else:
        # Обновляем тел.номер контакта, если он изменился
        if payload["crm.contact"]["contact_phone"] != contact["PHONE"][0]["VALUE"]:
            print("Обновляю телефонный номер контакта.")
            b.call(
                "crm.contact.update",
                {
                    "id": match_id[0],
                    "fields": {
                        "PHONE": [
                            {
                                "ID": contact["PHONE"][0]["ID"],
                                "VALUE": payload["crm.contact"]["contact_phone"]
                            }
                        ]
                    }
                }
            )
        contact_id = match_id[0]
    return contact_id


def get_deal_list():
    # Возвращает список незакрытых сделок, включая пользовательские поля
    # rtype: list[dict]
    deal_list = b.get_all(
        "crm.deal.list",
        params={
            'select': ['*', 'UF_*'],
            'filter': {'CLOSED': 'N'}
        }
    )
    return deal_list


def deal_add_update(deal_list, payload, contact_id):
    """
    Проверяет наличие на портале Битрикс24 сделки, указанной в заявке;
    создаёт новую сделку, если таковая на портале отсутствует, 
    или обновляет существующую сделку новыми данными;
    returns : deal_id - номер созданной/обновленной сделки
    rtype   : str
    """
    match_id = []   # Если сделка существует, добавляет ID сделки для дальнейшего обновления
    for deal in deal_list:
        if payload["crm.deal"]["deal_delivery_code"] == get_deal(deal["ID"])["UF_CRM_DELIVERY_CODE"]:
            print("Сделка с таким кодом доставки уже существует.")
            match_id.append(deal["ID"])
    if not match_id:
        print("Создаю новую сделку.")
        b.call(
            "crm.deal.add", {
                "fields": {
                    "TITLE": payload["crm.deal"]["deal_title"],
                    "TYPE_ID": "GOODS",
                    "STAGE_ID": "NEW",
                    "OPENED": "Y",
                    "CONTACT_ID": contact_id,
                    "UF_CRM_DESCRIPTION": payload["crm.deal"]["deal_description"],
                    "UF_CRM_DELIVERY_ADRESS": payload["crm.deal"]["deal_delivery_adress"],
                    "UF_CRM_DELIVERY_DATE": payload["crm.deal"]["deal_delivery_date"],
                    "UF_CRM_DELIVERY_CODE": payload["crm.deal"]["deal_delivery_code"],
                }
            }
        )
        # Если создается новая сделка, то ее ID будет в последнем словаре списка сделок
        deal_id = get_deal_list()[-1]["ID"]
    else:
        # Обновляем данные сделки
        print("Обновляю данные сделки.")
        b.call(
            "crm.deal.update",
            {
                "id": match_id[0],
                "fields": {
                    "TITLE": payload["crm.deal"]["deal_title"],
                    "UF_CRM_DESCRIPTION": payload["crm.deal"]["deal_description"],
                    "UF_CRM_DELIVERY_ADRESS": payload["crm.deal"]["deal_delivery_adress"],
                    "UF_CRM_DELIVERY_DATE": payload["crm.deal"]["deal_delivery_date"],
                }
            }
        )
        deal_id = match_id[0]
    return deal_id


def get_deal(id):
    # Возвращает сделку по идентификатору
    deal = b.get_all(
        "crm.deal.get",
        {"id": id}
    )
    return deal


def get_product_list():
    # Возвращает список товаров по фильтру
    product_list = b.get_all(
        "crm.product.list",
        {}
    )
    return product_list


def set_deal_products(deal_id, payload, product_list):
    """
    Устанавливает (создаёт или обновляет) товарные позиции сделки;
    из руководства Битрикс24: товарные позиции сделки, существующие 
    до момента вызова метода crm.deal.productrows.set, будут заменены 
    новыми.
    returns : None
    rtype   : None
    """
    products = []
    for product in product_list:
        products.append(
            {
                product["NAME"]: {
                    "ID": product["ID"], 
                    "PRICE": product["PRICE"],
                    "CURRENCY_ID": product["CURRENCY_ID"]
                }
            }
        )

    print("Добавляю товары в сделку.")
    rows = []
    for item in payload["crm.deal"]["deal_products"]:
        for product in products:
            if product.get(item):
                rows.append({
                    "PRODUCT_ID": product[item]["ID"],
                    "PRICE": product[item]["PRICE"],
                    "CURRENCY_ID":product[item]["CURRENCY_ID"],
                })
    
    b.call(
        "crm.deal.productrows.set", {
            "id": deal_id, 
            "rows": rows
        }
    )


def main(query_data):
    """Основная функция: запускает последовательность функций"""
    # Словарь имен пользовательских полей, которые должны быть в "Сделке"
    field_names = {
        "description": "Описание", 
        "delivery_adress": "Адрес доставки", 
        "delivery_date": "Дата доставки", 
        "delivery_code": "Код доставки",
    }

    deal_fields = get_deal_fields()
    add_deal_userfields(field_names, deal_fields)
    payload = generate_b24_data(query_data)
    contact_list = get_contact_list()
    contact_id = contact_add_update(contact_list, payload)
    deal_list = get_deal_list()
    deal_id = deal_add_update(deal_list, payload, contact_id)
    product_list = get_product_list()
    set_deal_products(deal_id, payload, product_list)


if __name__ == "__main__":
    import time

    # Имитированные заявки с сайта
    from test_queries import b24_query_1, b24_query_2, b24_query_3, b24_query_4

    main(b24_query_1)
    # time.sleep(2)
    # main(b24_query_2)
    # time.sleep(2)
    # main(b24_query_3)
    # time.sleep(2)
    # main(b24_query_4)

