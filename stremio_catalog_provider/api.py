from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from stremio_catalog_provider.container.default_container import DefaultContainer
from stremio_catalog_provider.controller.stremio_controller import StremioController
from stremio_catalog_provider.controller.web_ui_controller import WebUiController
from stremio_catalog_provider.controller.api_controller import ApiController

# Initialize the dependency injection container and FastAPI app
container = DefaultContainer.getInstance()
app: FastAPI = FastAPI(title="Stremio Custom Catalog Provider", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include the Stremio controller router
stremio_ctrl = container.get(StremioController)
app.include_router(stremio_ctrl.router)

# Include the Web UI controller router
web_ui_ctrl = container.get(WebUiController)
app.include_router(web_ui_ctrl.router)

# Include the API controller router
api_ctrl = container.get(ApiController)
app.include_router(api_ctrl.router)
