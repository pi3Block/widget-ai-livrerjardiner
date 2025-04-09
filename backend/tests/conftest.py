# Standard Library

from typing import AsyncGenerator, Optional

# Third-Party Libraries
import pytest
import pytest_asyncio

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

# First-Party Libraries (Your project)
from src.main import app
from src.database import get_db_session
from src.categories.models import Category
from src.tags.models import Tag
from src.products.models import Product
from src.product_variants.models import ProductVariant
from src.users.models import UserBase
from src.auth.security import get_password_hash, create_access_token
from src.pdf.dependencies import get_pdf_generator
from src.pdf.generator import AbstractPDFGenerator
from src.pdf.exceptions import PDFGenerationException, TemplateNotFoundException
from src.pdf.models import PDFQuoteData

# URL de base pour la DB en mémoire
TEST_DATABASE_BASE_URL = "sqlite+aiosqlite:///:memory:"

# --- Fixtures de Base ---

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Crée un engine, des tables, et fournit une session DB en mémoire pour chaque test."""
    # Créer un engine spécifiques à ce test
    engine: AsyncEngine = create_async_engine(TEST_DATABASE_BASE_URL, echo=False)
    
    # Créer les tables dans cet engine
    async with engine.begin() as conn:
        # Toutes les tables (SQLModel et SQLAlchemy Base) utilisent maintenant
        # SQLModel.metadata grâce à la configuration de Base.
        # Un seul appel à create_all suffit.
        await conn.run_sync(SQLModel.metadata.create_all)

    # Créer une session factory liée à cet engine
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Fournir la session
    async with TestingSessionLocal() as session:
        yield session

    # Nettoyage (drop tables et dispose engine)
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all) # Pas nécessaire avec :memory:
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def test_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Fournit un AsyncClient httpx qui utilise la session DB de test isolée."""
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    del app.dependency_overrides[get_db_session]

# --- Fixtures Utilisateur et Authentification ---

@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> UserBase:
    """Crée un utilisateur standard. Commit nécessaire pour auth_headers."""
    hashed_password = get_password_hash("testpassword")
    user = UserBase(
        email="testuser@example.com",
        password_hash=hashed_password,
        name="Test User",
        is_admin=False
    )
    db_session.add(user)
    await db_session.commit() # Commit pour obtenir l'ID
    await db_session.refresh(user) # Refresh pour charger l'ID
    return user

@pytest_asyncio.fixture(scope="function")
async def admin_user(db_session: AsyncSession) -> UserBase:
    """Crée un utilisateur admin. Commit nécessaire pour auth_headers."""
    hashed_password = get_password_hash("adminpassword")
    user = UserBase(
        email="admin@example.com",
        password_hash=hashed_password,
        name="Admin User",
        is_admin=True
    )
    db_session.add(user)
    await db_session.commit() # Commit pour obtenir l'ID
    await db_session.refresh(user) # Refresh pour charger l'ID
    return user

@pytest_asyncio.fixture(scope="function")
async def auth_headers_user(test_user: UserBase) -> dict[str, str]: # db_session n'est plus nécessaire ici
    """Génère les headers d'authentification pour l'utilisateur standard."""
    # La fixture test_user a déjà commité et refreshé
    if test_user.id is None:
         pytest.fail("L'ID de test_user est None après commit/refresh dans la fixture test_user.")
    access_token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {access_token}"}

@pytest_asyncio.fixture(scope="function")
async def auth_headers_admin(admin_user: UserBase) -> dict[str, str]: # db_session n'est plus nécessaire ici
    """Génère les headers d'authentification pour l'utilisateur admin."""
    # La fixture admin_user a déjà commité et refreshé
    if admin_user.id is None:
         pytest.fail("L'ID de admin_user est None après commit/refresh dans la fixture admin_user.")
    access_token = create_access_token(data={"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {access_token}"}

# Fixtures pour un deuxième utilisateur standard
@pytest_asyncio.fixture(scope="function")
async def test_user_2(db_session: AsyncSession) -> UserBase:
    """Crée un deuxième utilisateur standard. Commit nécessaire pour auth_headers."""
    hashed_password = get_password_hash("testpassword2")
    user = UserBase(
        email="testuser2@example.com",
        password_hash=hashed_password,
        name="Test User 2",
        is_admin=False
    )
    db_session.add(user)
    await db_session.commit() # Commit pour obtenir l'ID
    await db_session.refresh(user) # Refresh pour charger l'ID
    return user

@pytest_asyncio.fixture(scope="function")
async def auth_headers_user_2(test_user_2: UserBase) -> dict[str, str]: # db_session n'est plus nécessaire ici
    """Génère les headers d'authentification pour le deuxième utilisateur standard."""
    # La fixture test_user_2 a déjà commité et refreshé
    if test_user_2.id is None:
         pytest.fail("L'ID de test_user_2 est None après commit/refresh dans la fixture test_user_2.")
    access_token = create_access_token(data={"sub": str(test_user_2.id)})
    return {"Authorization": f"Bearer {access_token}"}

# --- Fixtures Produits ---
# Commit/refresh sont toujours là, semble nécessaire pour les tests produits

@pytest_asyncio.fixture(scope="function")
async def test_category(db_session: AsyncSession) -> Category:
    """Crée une catégorie de test."""
    # Utiliser le modèle Category SQLModel
    category = Category(name="Test Cat", description="Test Desc") 
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category

@pytest_asyncio.fixture(scope="function")
async def test_tag(db_session: AsyncSession) -> Tag:
    """Crée un tag de test."""
    tag = Tag(name="Test Tag")
    db_session.add(tag)
    await db_session.commit()
    await db_session.refresh(tag)
    return tag

@pytest_asyncio.fixture(scope="function")
async def test_product(db_session: AsyncSession, test_category: Category, test_tag: Tag) -> Product:
    """Crée un produit de test avec catégorie et tag."""
    category = test_category
    tag = test_tag
    product = Product(
        name="Test Product",
        base_description="Test Product Description",
        category_id=category.id,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    # Créer une variante liée à ce produit pour pouvoir lier le tag
    # (Sinon, la fixture test_product ne représente pas un état valide)
    # NOTE: Ceci pourrait être une fixture séparée ou intégrée si nécessaire partout
    variant = ProductVariant(
        product_id=product.id,
        sku=f"TEST-PROD-{product.id}-VAR",
        price=9.99,
        tags=[tag] # Lier le tag à la variante
    )
    db_session.add(variant)
    await db_session.commit()
    # Rafraîchir product n'est pas nécessaire pour lier le tag à la variante
    # await db_session.refresh(product)
    
    return product

@pytest_asyncio.fixture(scope="function")
async def test_variant(db_session: AsyncSession, test_product: Product) -> ProductVariant:
    """Crée une variante de produit de test."""
    product = test_product
    variant = ProductVariant(
        product_id=product.id,
        sku="TEST-SKU-123",
        price=19.99,
        attributes={"size": "M", "color": "Blue"}
    )
    db_session.add(variant)
    await db_session.commit()
    await db_session.refresh(variant)
    return variant 

# --- Fixtures PDF ---

class MockPDFGenerator(AbstractPDFGenerator):
    """Un générateur PDF simulé pour les tests."""

    # Implémentation fictive pour generate_quote_pdf
    async def generate_quote_pdf(
        self,
        quote_data: PDFQuoteData,
        output_path: Optional[str] = None
    ) -> bytes:
        """Simule la génération d'un devis PDF."""
        print(f"MockPDFGenerator: Simulating quote PDF generation for quote ID {quote_data.quote_id}...")
        if quote_data.quote_id == "fail_quote": # Exemple de condition d'échec
             print("MockPDFGenerator: Simulating quote failure.")
             raise PDFGenerationException("Mock quote generation failed intentionally.")
        
        mock_content = f"Mock PDF content for quote {quote_data.quote_id}".encode('utf-8')
        if output_path:
            print(f"MockPDFGenerator: Simulating saving quote PDF to {output_path}")
            # Dans un vrai mock, on pourrait écrire un fichier fictif
            pass 
        return mock_content

    # Renommer les paramètres pour correspondre à la définition de l'interface
    async def generate_pdf(
        self,
        template_name: str,
        context: dict, # Correspond à 'context' dans l'interface
        output_path: Optional[str] = None
    ) -> bytes: # L'interface retourne des bytes
        """Simule la génération de PDF à partir d'un template."""
        print(f"MockPDFGenerator: Simulating PDF generation for template '{template_name}'...")
        if template_name == "fail_template":
            print("MockPDFGenerator: Simulating failure.")
            raise PDFGenerationException("Mock generation failed intentionally for testing.")
        if template_name == "not_found_template":
            print("MockPDFGenerator: Simulating template not found.")
            # Fournir un search_path fictif
            raise TemplateNotFoundException(template_name=template_name, search_path="/mock/templates")

        # Retourne un contenu binaire fictif
        mock_content = f"Mock PDF content for {template_name} with data {context}".encode('utf-8')
        if output_path:
            # Simuler la sauvegarde si nécessaire
            print(f"MockPDFGenerator: Simulating saving PDF to {output_path}")
            # with open(output_path, 'wb') as f:
            #     f.write(mock_content)
        
        return mock_content

@pytest_asyncio.fixture(scope="function") # Utiliser 'function' scope si on veut le mock par défaut
async def test_client_with_mock_pdf(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Fournit un AsyncClient httpx utilisant la session DB de test
    ET un générateur PDF mocké.
    """
    # Override DB session
    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    # Override PDF Generator
    async def override_get_pdf_generator() -> AbstractPDFGenerator:
        # Maintenant, MockPDFGenerator implémente toutes les méthodes abstraites
        return MockPDFGenerator()

    original_db_override = app.dependency_overrides.get(get_db_session)
    original_pdf_override = app.dependency_overrides.get(get_pdf_generator)

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_pdf_generator] = override_get_pdf_generator # Activer le mock

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    # Restore original overrides or clear them
    if original_db_override:
        app.dependency_overrides[get_db_session] = original_db_override
    else:
        del app.dependency_overrides[get_db_session]

    if original_pdf_override:
         app.dependency_overrides[get_pdf_generator] = original_pdf_override
    else:
        # Check if the key exists before deleting, prevents KeyError if it wasn't there
        if get_pdf_generator in app.dependency_overrides:
             del app.dependency_overrides[get_pdf_generator]
