# Django Trading Signal Service

## Installation and Setup 
python -m venv venv
venv\Scripts\activate

## Install dependencies
pip install -r requirements.txt

## Database setup
```
env
Database_url=sqlite:///db.sqlite3
```
## Apply database migration
python manage.py migrate

## Create super user
python manage.py createsuperuser
## Run the server
python manage.py runserver

---
## Api Documentation
First login with your credential and then access the api
in the api you can find the following endpoints:
```  http://127.0.0.1:8000/api-auth/login/ 
```
---
## Signal 
endpoints would be -
``` 
http://127.0.0.1:8000/api/v1/signal/ 

```
input data for it would be -
```
BUY EURUSD @1.0860
SL 1.0850
TP 1.0890
```
---
## Order
endpoints would be -
```

http://127.0.0.1:8000/api/v1/order/

```
input data for it would be to create order-
"signal" : "uuid of trading signal",
"broker_account" : "uuid  of broker account"

---
## Broker 
endpoints would be-
``` 
http://127.0.0.1:8000/api/v1/broker/

```
input data for it would be to create broker-
"broker_name" : "broker_name",
"account_name": "account_name",
"api_key": "api_key",
"server" : "",
"is_demo" : true
# Change the is_demo to false when you want to use real broker
---

## Project Structure
``` 
trading_system/ #Project Settings
signals/   # webhook reception and signal parsing
orders/    # Order lifecycle management
brokers/   # Broker account management
api/       # api versioning
