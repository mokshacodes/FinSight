from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.models import Price, Metric
from app.schemas.schemas import PriceCreate, MetricCreate

def create_price(db: Session, price: PriceCreate):
    db_price = Price(**price.dict())
    db.add(db_price)
    db.commit()
    db.refresh(db_price)
    return db_price

def create_metric(db: Session, metric: MetricCreate):
    db_metric = Metric(**metric.dict())
    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)
    return db_metric

def get_price(db: Session, price_id: int):
    return db.query(Price).filter(Price.id == price_id).first()

def get_metric(db: Session, metric_id: int):
    return db.query(Metric).filter(Metric.id == metric_id).first()