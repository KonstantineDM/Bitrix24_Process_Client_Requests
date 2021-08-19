# Bitrix24_Process_Client_Requests
Скрипт ожидает заявку клиента с сайта; после получения направляет ее на портал Битрикс24, создавая при этом "Контакт" и "Сделку" из данных, указанных в полученной заявке.

Также, при первом запуске, скрипт создает пользовательские поля в разделе "Сделки".

Для корректной работы, на портале должен быть создан входящий вебхук с правом доступа CRM(crm), url-адрес которого надо поместить в переменную WEBHOOK в файле .env (в корне).

Перечень товаров, с их ценами, должен быть заранее создан на портале (данная функция в скрипте не предусмотрена).

## Принцип работы

Запускать необходимо только файл `server.py`.

Файл запускает серевер Flask, который настроен на ожидание входящей заявки. 

Имитация работы сайта, подающего заявку, выполнялась с помощью Postman.
Обмен данными с порталом Битрикс24 осуществляется с помощью библиотеки fast_bitrix24 через вебхук.

Заявка представляет из себя файл JSON в следующем формате:
```
{
    "title": "Название",
    "description": "Описание",
    "client": {
        "name": "Имя",
        "surname": "Фамилия",
        "phone": "+7ХХХХХХХХХХ",
        "adress": "Адрес клиента"
    },
    "products": [
        "Товар_1",
        "Товар_2",
        "Товар_3"
    ],
    "delivery_adress": "Адрес доставки",
    "delivery_date": "Дата доставки",
    "delivery_code": "Уникальный код доставки"
}
```

При поступлении заявки, данные из нее передаются в виде аргумента в функцию `main()`, импортируемую из файла `query_script.py`.

Функция `main()` последовательно вызывает функции, в т.ч. использующие методы Битрикс24, для:
1. Получения существующих полей в форме "Сделки" на портале Битрикс24;
2. Создания недостающих пользовательских полей (имена полей содержатся в переменной `field_names` в теле функции `main()`);
3. Формирования данных о "Сделке" и "Клиенте" из заявки;
4. Получения существующих "Контактов" на портале;
5. Создания нового "Контакта" или обновления существующего;
6. Получения существующих "Сделок" на портале;
7. Создания новой "Сделки" или обновления существующей;
8. Получения существующих "Товаров" на портале;
9. Внесения информации о товарах из заявки в "Сделку".

В случае, если поступившая заявка имеет "delivery_code" идентичный содержавшемуся в одной из предыдущих заявок, данные из более новой заявки имеют приоритет и заменяют данные, поступившие в "Сделку" из предыдущей заявки.

## Зависимости

Flask

fast-bitrix24

python-dotenv