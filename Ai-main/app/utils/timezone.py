"""
한국 시간(KST) 유틸리티
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

# 한국 시간대 (UTC+9)
KST = timezone(timedelta(hours=9))

def now_kst() -> datetime:
    """현재 한국 시간 반환"""
    return datetime.now(KST)

def utc_to_kst(utc_dt: datetime) -> datetime:
    """UTC 시간을 한국 시간으로 변환"""
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(KST)

def kst_to_utc(kst_dt: datetime) -> datetime:
    """한국 시간을 UTC로 변환"""
    if kst_dt.tzinfo is None:
        kst_dt = kst_dt.replace(tzinfo=KST)
    return kst_dt.astimezone(timezone.utc)

def format_kst_datetime(dt: Optional[datetime] = None) -> str:
    """한국 시간을 ISO 형식으로 포맷 (프론트엔드용)"""
    if dt is None:
        dt = now_kst()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    elif dt.tzinfo != KST:
        dt = dt.astimezone(KST)
    
    return dt.isoformat()

def format_kst_date(dt: Optional[datetime] = None) -> str:
    """한국 시간을 날짜 형식으로 포맷 (YYYY-MM-DD)"""
    if dt is None:
        dt = now_kst()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    elif dt.tzinfo != KST:
        dt = dt.astimezone(KST)
    
    return dt.strftime('%Y-%m-%d')

def format_kst_timestamp(dt: Optional[datetime] = None) -> str:
    """한국 시간을 타임스탬프 형식으로 포맷 (YYYYMMDD_HHMMSS)"""
    if dt is None:
        dt = now_kst()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    elif dt.tzinfo != KST:
        dt = dt.astimezone(KST)
    
    return dt.strftime('%Y%m%d_%H%M%S')