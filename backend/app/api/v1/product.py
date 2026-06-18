from fastapi import APIRouter, HTTPException, Query

from backend.app.services.product_service import ProductService

router = APIRouter()
product_service = ProductService()


@router.get("")
async def list_products():
    return await product_service.list_products()


@router.get("/search")
async def search_products(keyword: str = Query("", min_length=0)):
    return await product_service.search_products(keyword)


@router.get("/{product_id}")
async def get_product(product_id: str):
    product = await product_service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product
