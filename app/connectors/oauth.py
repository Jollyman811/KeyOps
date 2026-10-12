from authlib.integrations.starlette_client import OAuth
from ..config import settings
def get_oauth():
    oauth = OAuth()
    oauth.register(
        name='google',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/calendar.events'}
    )
    oauth.register(
        name='stripe',
        client_id=settings.STRIPE_CLIENT_ID,
        client_secret=settings.STRIPE_CLIENT_SECRET,
        api_base_url='https://connect.stripe.com/',
        access_token_url='https://connect.stripe.com/oauth/token',
        authorize_url='https://connect.stripe.com/oauth/authorize',
        client_kwargs={'scope':'read_write'}
    )
    oauth.register(
        name='intuit',
        client_id=settings.INTUIT_CLIENT_ID,
        client_secret=settings.INTUIT_CLIENT_SECRET,
        api_base_url='https://quickbooks.api.intuit.com',
        access_token_url='https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer',
        authorize_url='https://appcenter.intuit.com/connect/oauth2',
        client_kwargs={'scope':'com.intuit.quickbooks.accounting'}
    )
    return oauth
