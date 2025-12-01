"""Blog API routes for admin management and public access."""

import uuid
import base64
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel, EmailStr, Field

from app.api.dependencies import get_redis_client
from app.api.routes.auth import get_current_user


# Models
class BlogPostCreate(BaseModel):
    title: str = Field(..., min_length=1)
    slug: Optional[str] = None
    content: str = Field(..., min_length=1)
    excerpt: Optional[str] = None
    featured_image: Optional[str] = None
    tags: List[str] = []
    status: str = "draft"
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None


class BlogPostUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    featured_image: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None


class SubscribeRequest(BaseModel):
    email: EmailStr
    frequency: str = "weekly"


# Routers
router = APIRouter()
admin_router = APIRouter(prefix="/admin/blog", tags=["blog-admin"])
public_router = APIRouter(prefix="/blog", tags=["blog"])
upload_router = APIRouter(prefix="/uploads", tags=["uploads"])


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    import re
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug


# Admin Routes
@admin_router.get("/posts")
async def list_posts(
    current_user: dict = Depends(get_current_user),
    redis = Depends(get_redis_client)
):
    """List all blog posts (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    post_keys = await redis.keys("blog:post:*")
    posts = []

    for key in post_keys:
        post_data = await redis.get(key)
        if post_data:
            posts.append({
                "id": post_data.get("id"),
                "title": post_data.get("title"),
                "slug": post_data.get("slug"),
                "status": post_data.get("status", "draft"),
                "author_id": post_data.get("author_id"),
                "author_name": post_data.get("author_name", "Unknown"),
                "view_count": post_data.get("view_count", 0),
                "created_at": post_data.get("created_at"),
                "updated_at": post_data.get("updated_at"),
            })

    # Sort by created_at descending
    posts.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {"posts": posts}


@admin_router.get("/posts/{post_id}")
async def get_post_admin(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    redis = Depends(get_redis_client)
):
    """Get a single blog post by ID (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    post_data = await redis.get(f"blog:post:{post_id}")
    if not post_data:
        raise HTTPException(status_code=404, detail="Post not found")

    return {
        "id": post_data.get("id"),
        "title": post_data.get("title"),
        "slug": post_data.get("slug"),
        "content": post_data.get("content"),
        "excerpt": post_data.get("excerpt"),
        "featured_image": post_data.get("featured_image"),
        "tags": post_data.get("tags", []),
        "status": post_data.get("status", "draft"),
        "author_id": post_data.get("author_id"),
        "author_name": post_data.get("author_name"),
        "view_count": post_data.get("view_count", 0),
        "meta_description": post_data.get("meta_description"),
        "meta_keywords": post_data.get("meta_keywords"),
        "created_at": post_data.get("created_at"),
        "updated_at": post_data.get("updated_at"),
        "published_at": post_data.get("published_at"),
    }


@admin_router.post("/posts")
async def create_post(
    post: BlogPostCreate,
    current_user: dict = Depends(get_current_user),
    redis = Depends(get_redis_client)
):
    """Create a new blog post (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    post_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    slug = post.slug if post.slug else slugify(post.title)

    # Check for duplicate slug
    existing_slugs = await redis.smembers("blog:slugs")
    if slug in existing_slugs:
        slug = f"{slug}-{post_id[:8]}"

    post_data = {
        "id": post_id,
        "title": post.title,
        "slug": slug,
        "content": post.content,
        "excerpt": post.excerpt or "",
        "featured_image": post.featured_image or "",
        "tags": post.tags,
        "status": post.status,
        "author_id": current_user.get("user_id", current_user.get("id", "")),
        "author_name": current_user.get("name", current_user.get("email", "Admin")),
        "view_count": 0,
        "meta_description": post.meta_description or "",
        "meta_keywords": post.meta_keywords or "",
        "created_at": now,
        "updated_at": now,
    }

    if post.status == "published":
        post_data["published_at"] = now

    await redis.set(f"blog:post:{post_id}", post_data)
    await redis.sadd("blog:slugs", slug)
    await redis.sadd("blog:post_ids", post_id)

    return {"id": post_id, "slug": slug, "message": "Post created successfully"}


@admin_router.patch("/posts/{post_id}")
async def update_post(
    post_id: str,
    post: BlogPostUpdate,
    current_user: dict = Depends(get_current_user),
    redis = Depends(get_redis_client)
):
    """Update a blog post (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    existing = await redis.get(f"blog:post:{post_id}")
    if not existing:
        raise HTTPException(status_code=404, detail="Post not found")

    now = datetime.utcnow().isoformat()
    existing["updated_at"] = now

    if post.title is not None:
        existing["title"] = post.title
    if post.slug is not None:
        # Remove old slug from set
        old_slug = existing.get("slug")
        if old_slug:
            await redis.srem("blog:slugs", old_slug)
        existing["slug"] = post.slug
        await redis.sadd("blog:slugs", post.slug)
    if post.content is not None:
        existing["content"] = post.content
    if post.excerpt is not None:
        existing["excerpt"] = post.excerpt
    if post.featured_image is not None:
        existing["featured_image"] = post.featured_image
    if post.tags is not None:
        existing["tags"] = post.tags
    if post.status is not None:
        existing["status"] = post.status
        if post.status == "published" and not existing.get("published_at"):
            existing["published_at"] = now
    if post.meta_description is not None:
        existing["meta_description"] = post.meta_description
    if post.meta_keywords is not None:
        existing["meta_keywords"] = post.meta_keywords

    await redis.set(f"blog:post:{post_id}", existing)

    return {"message": "Post updated successfully"}


@admin_router.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    redis = Depends(get_redis_client)
):
    """Delete a blog post (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    existing = await redis.get(f"blog:post:{post_id}")
    if not existing:
        raise HTTPException(status_code=404, detail="Post not found")

    # Remove slug from set
    slug = existing.get("slug")
    if slug:
        await redis.srem("blog:slugs", slug)

    await redis.delete(f"blog:post:{post_id}")
    await redis.srem("blog:post_ids", post_id)

    return {"message": "Post deleted successfully"}


@admin_router.get("/subscriptions")
async def list_subscriptions(
    current_user: dict = Depends(get_current_user),
    redis = Depends(get_redis_client)
):
    """List all blog subscriptions (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    sub_keys = await redis.keys("blog:subscription:*")
    subscriptions = []

    for key in sub_keys:
        sub_data = await redis.get(key)
        if sub_data:
            subscriptions.append({
                "id": sub_data.get("id"),
                "email": sub_data.get("email"),
                "status": sub_data.get("status", "active"),
                "frequency": sub_data.get("frequency", "weekly"),
                "created_at": sub_data.get("created_at"),
                "last_notified_at": sub_data.get("last_notified_at"),
            })

    # Sort by created_at descending
    subscriptions.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {"subscriptions": subscriptions}


@admin_router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user),
    redis = Depends(get_redis_client)
):
    """Delete a subscription (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    existing = await redis.exists(f"blog:subscription:{subscription_id}")
    if not existing:
        raise HTTPException(status_code=404, detail="Subscription not found")

    await redis.delete(f"blog:subscription:{subscription_id}")

    return {"message": "Subscription deleted successfully"}


# Public Routes
@public_router.get("/posts")
async def list_published_posts(
    tag: Optional[str] = None,
    redis = Depends(get_redis_client)
):
    """List all published blog posts."""
    post_keys = await redis.keys("blog:post:*")
    posts = []

    for key in post_keys:
        post_data = await redis.get(key)
        if post_data and post_data.get("status") == "published":
            tags = post_data.get("tags", [])

            # Filter by tag if specified
            if tag and tag not in tags:
                continue

            posts.append({
                "id": post_data.get("id"),
                "title": post_data.get("title"),
                "slug": post_data.get("slug"),
                "excerpt": post_data.get("excerpt"),
                "featured_image": post_data.get("featured_image"),
                "tags": tags,
                "author_name": post_data.get("author_name"),
                "view_count": post_data.get("view_count", 0),
                "published_at": post_data.get("published_at"),
            })

    # Sort by published_at descending
    posts.sort(key=lambda x: x.get("published_at", ""), reverse=True)

    return {"posts": posts}


@public_router.get("/posts/{slug}")
async def get_post_by_slug(
    slug: str,
    redis = Depends(get_redis_client)
):
    """Get a published blog post by slug."""
    # Find post by slug
    post_keys = await redis.keys("blog:post:*")
    for key in post_keys:
        post_data = await redis.get(key)
        if post_data and post_data.get("slug") == slug:
            if post_data.get("status") != "published":
                raise HTTPException(status_code=404, detail="Post not found")

            # Increment view count
            post_data["view_count"] = post_data.get("view_count", 0) + 1
            await redis.set(key, post_data)

            return {
                "id": post_data.get("id"),
                "title": post_data.get("title"),
                "slug": post_data.get("slug"),
                "content": post_data.get("content"),
                "excerpt": post_data.get("excerpt"),
                "featured_image": post_data.get("featured_image"),
                "tags": post_data.get("tags", []),
                "author_name": post_data.get("author_name"),
                "view_count": post_data.get("view_count", 0),
                "meta_description": post_data.get("meta_description"),
                "meta_keywords": post_data.get("meta_keywords"),
                "published_at": post_data.get("published_at"),
            }

    raise HTTPException(status_code=404, detail="Post not found")


@public_router.post("/subscribe")
async def subscribe(
    request: SubscribeRequest,
    redis = Depends(get_redis_client)
):
    """Subscribe to blog updates."""
    # Check if already subscribed
    sub_keys = await redis.keys("blog:subscription:*")
    for key in sub_keys:
        sub_data = await redis.get(key)
        if sub_data and sub_data.get("email") == request.email:
            if sub_data.get("status") == "active":
                return {"message": "Already subscribed"}
            else:
                # Reactivate subscription
                sub_data["status"] = "active"
                await redis.set(key, sub_data)
                return {"message": "Subscription reactivated"}

    sub_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    sub_data = {
        "id": sub_id,
        "email": request.email,
        "status": "active",
        "frequency": request.frequency,
        "created_at": now,
    }

    await redis.set(f"blog:subscription:{sub_id}", sub_data)

    return {"message": "Successfully subscribed to blog updates"}


@public_router.post("/unsubscribe")
async def unsubscribe(
    email: str,
    redis = Depends(get_redis_client)
):
    """Unsubscribe from blog updates."""
    sub_keys = await redis.keys("blog:subscription:*")
    for key in sub_keys:
        sub_data = await redis.get(key)
        if sub_data and sub_data.get("email") == email:
            sub_data["status"] = "unsubscribed"
            await redis.set(key, sub_data)
            return {"message": "Successfully unsubscribed"}

    raise HTTPException(status_code=404, detail="Subscription not found")


# Upload Routes
@upload_router.post("/blog-image")
async def upload_blog_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    redis = Depends(get_redis_client)
):
    """Upload a blog image (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: JPEG, PNG, GIF, WebP")

    # Read file content
    content = await file.read()

    # Check file size (5MB max)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 5MB")

    # Generate unique filename
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    image_id = str(uuid.uuid4())
    filename = f"{image_id}.{ext}"

    # Store image as base64 in Redis (for simplicity - in production use S3/CDN)
    image_data = {
        "id": image_id,
        "filename": filename,
        "content_type": file.content_type,
        "data": base64.b64encode(content).decode("utf-8"),
        "created_at": datetime.utcnow().isoformat(),
    }

    await redis.set(f"blog:image:{image_id}", image_data)

    # Return URL that will serve the image
    return {"url": f"/api/uploads/images/{image_id}"}


@upload_router.get("/images/{image_id}")
async def get_image(
    image_id: str,
    redis = Depends(get_redis_client)
):
    """Serve an uploaded image."""
    from fastapi.responses import Response

    image_data = await redis.get(f"blog:image:{image_id}")
    if not image_data:
        raise HTTPException(status_code=404, detail="Image not found")

    content = base64.b64decode(image_data.get("data", ""))
    content_type = image_data.get("content_type", "image/jpeg")

    return Response(content=content, media_type=content_type)
