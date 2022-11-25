### :dart: Bright Money Task

### :computer: Local Enviornment Setup

    1. Create and Enter virtual enviorment
          virtualenv env
          source env/bin/activate

    2. Install all dependencies
          pip3 install -r requirements.txt

    3. Setup Models
          python3 manage.py makemigrations
          python3 manage.py migrate

    4. Run server
          python3 manage.py runserver

    5. Start celery worker
          celery -A core worker -l info

### Users API

    /users                               => For registering user
    /jwt/create/                         => For logging in user
    /jwt/refresh/                        => For obtaining refresh token

### Token Exchange API (Get Method)

    /api/get_items/            =>  Get All Items
    /api/get_accounts/         =>  Get All Accounts
    /api/get_transactios/      =>  Get All Transaction
    /api/transaction_webhook/  =>  Transaction Webhook

### :anchor: Token Exchange API (Post Method)

    /api/link_token/           => Get Plain Link Token
    /api/get_access_token/     => Plaid-Link-Public_token (exchange public token with access_token)
