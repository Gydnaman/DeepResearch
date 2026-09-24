from .service import create_app

app = create_app(initialize_schema=False)
