"""
Router para gestión de productos comerciales del usuario.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from app.security.auth import get_current_regular_user
from app.db import products as products_db

router = APIRouter(prefix="/products", tags=["products"])

# Inicializar DB al importar
products_db.init_products_db()


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: float = Field(..., gt=0)
    sku: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=100)
    stock: int = Field(default=0, ge=0)
    active: bool = True


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[float] = Field(None, gt=0)
    sku: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=100)
    stock: Optional[int] = Field(None, ge=0)
    active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    price: float
    sku: Optional[str]
    category: Optional[str]
    stock: int
    active: bool
    created_at: str
    updated_at: str


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    current_user: dict = Depends(get_current_regular_user)
):
    """Crea un nuevo producto para el usuario actual."""
    product_id = products_db.create_product(
        user_id=current_user["id"],
        name=product.name,
        description=product.description,
        price=product.price,
        sku=product.sku,
        category=product.category,
        stock=product.stock,
        active=product.active
    )
    
    created_product = products_db.get_product(product_id, current_user["id"])
    return ProductResponse(**created_product)


@router.get("/", response_model=List[ProductResponse])
async def list_products(
    category: Optional[str] = None,
    active_only: bool = True,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_regular_user)
):
    """Lista todos los productos del usuario actual."""
    products = products_db.list_products(
        user_id=current_user["id"],
        category=category,
        active_only=active_only,
        search=search
    )
    return [ProductResponse(**p) for p in products]


@router.get("/categories", response_model=List[str])
async def get_categories(current_user: dict = Depends(get_current_regular_user)):
    """Obtiene todas las categorías de productos del usuario."""
    return products_db.get_categories(current_user["id"])


@router.get("/count")
async def get_product_count(
    active_only: bool = True,
    current_user: dict = Depends(get_current_regular_user)
):
    """Obtiene el conteo de productos del usuario."""
    count = products_db.get_product_count(current_user["id"], active_only)
    return {"count": count}


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    current_user: dict = Depends(get_current_regular_user)
):
    """Obtiene un producto específico del usuario."""
    product = products_db.get_product(product_id, current_user["id"])
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    return ProductResponse(**product)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_update: ProductUpdate,
    current_user: dict = Depends(get_current_regular_user)
):
    """Actualiza un producto del usuario."""
    success = products_db.update_product(
        product_id=product_id,
        user_id=current_user["id"],
        name=product_update.name,
        description=product_update.description,
        price=product_update.price,
        sku=product_update.sku,
        category=product_update.category,
        stock=product_update.stock,
        active=product_update.active
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    
    updated_product = products_db.get_product(product_id, current_user["id"])
    return ProductResponse(**updated_product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    hard_delete: bool = False,
    current_user: dict = Depends(get_current_regular_user)
):
    """Elimina un producto del usuario (soft delete por defecto)."""
    if hard_delete:
        success = products_db.hard_delete_product(product_id, current_user["id"])
    else:
        success = products_db.delete_product(product_id, current_user["id"])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    
    return None
