"""Air Quality Intelligence & Sub-Index Calculation Engine API."""

from enum import Enum
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

app = FastAPI(
    title="Air Quality Sub-Index & Environmental Intelligence API",
    description="Microservice for calculating CPCB-compliant AQI, identifying dominant toxic drivers, and issuing dynamic health advisories.",
    version="1.0.0",
)

# --- Standard Breakpoint Definitions (CPCB / NAAQS Standards) ---
BREAKPOINTS = {
    "PM2.5": [
        (0.0, 30.0, 0, 50),
        (30.1, 60.0, 51, 100),
        (60.1, 90.0, 101, 200),
        (90.1, 120.0, 201, 300),
        (120.1, 250.0, 301, 400),
        (250.1, 500.0, 401, 500),
    ],
    "PM10": [
        (0.0, 50.0, 0, 50),
        (50.1, 100.0, 51, 100),
        (100.1, 250.0, 101, 200),
        (250.1, 350.0, 201, 300),
        (350.1, 430.0, 301, 400),
        (430.1, 600.0, 401, 500),
    ],
    "NO2": [
        (0.0, 40.0, 0, 50),
        (40.1, 80.0, 51, 100),
        (80.1, 180.0, 101, 200),
        (180.1, 280.0, 201, 300),
        (280.1, 400.0, 301, 400),
        (400.1, 600.0, 401, 500),
    ],
    "SO2": [
        (0.0, 40.0, 0, 50),
        (40.1, 80.0, 51, 100),
        (80.1, 380.0, 101, 200),
        (380.1, 800.0, 201, 300),
        (800.1, 1600.0, 301, 400),
        (1600.1, 2000.0, 401, 500),
    ],
    "CO": [
        (0.0, 1.0, 0, 50),
        (1.01, 2.0, 51, 100),
        (2.01, 10.0, 101, 200),
        (10.01, 17.0, 201, 300),
        (17.01, 34.0, 301, 400),
        (34.01, 50.0, 401, 500),
    ],
}


def compute_sub_index(
    conc: float, breakpoints: List[tuple[float, float, int, int]]
) -> float:
    """Piecewise linear interpolation formula:

    I = [ (I_hi - I_lo) / (B_hi - B_lo) ] * (C - B_lo) + I_lo
    """
    conc = max(0.0, conc)
    for b_lo, b_hi, i_lo, i_hi in breakpoints:
        if b_lo <= conc <= b_hi:
            return ((i_hi - i_lo) / (b_hi - b_lo)) * (conc - b_lo) + i_lo
    # If concentration exceeds upper boundary scale up to max bracket
    return float(breakpoints[-1][3])


class SensorInputSchema(BaseModel):
    pm25: float = Field(
        ...,
        ge=0.0,
        le=1000.0,
        description="PM2.5 concentration in ug/m3",
        example=55.4,
    )
    pm10: float = Field(
        ...,
        ge=0.0,
        le=1500.0,
        description="PM10 concentration in ug/m3",
        example=88.2,
    )
    no2: float = Field(
        ...,
        ge=0.0,
        le=1000.0,
        description="Nitrogen Dioxide in ug/m3",
        example=42.1,
    )
    so2: float = Field(
        ...,
        ge=0.0,
        le=2000.0,
        description="Sulfur Dioxide in ug/m3",
        example=12.5,
    )
    co: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Carbon Monoxide in mg/m3",
        example=2.3,
    )
    nox: Optional[float] = Field(
        None, description="Total Nitrogen Oxides (ppb)", example=85.0
    )
    vocs: Optional[float] = Field(
        None,
        description="Volatile Organic Compounds in ppb",
        example=110.0,
    )
    co2: Optional[float] = Field(
        None, description="Carbon Dioxide in ppm", example=420.0
    )
    ch4: Optional[float] = Field(
        None, description="Methane in ppm", example=2.1
    )
    temperature: Optional[float] = Field(
        None, description="Ambient temperature in Celsius", example=28.5
    )


class AQIResponseSchema(BaseModel):
    overall_aqi: float
    category: str
    dominant_pollutant: str
    sub_indices: Dict[str, float]
    color_hex: str
    health_advisory: str
    actionable_guidance: str


def evaluate_category(aqi: float):
    if aqi <= 50:
        return (
            "Good",
            "#2ecc71",
            "Air quality is satisfactory and poses minimal risk.",
            "Ideal conditions for outdoor activity.",
        )
    elif aqi <= 100:
        return (
            "Satisfactory",
            "#f1c40f",
            "Minor breathing discomfort to sensitive individuals.",
            "Sensitive groups should monitor symptoms.",
        )
    elif aqi <= 200:
        return (
            "Moderate",
            "#e67e22",
            "Breathing discomfort to people with lung, asthma, and heart diseases.",
            "Consider reducing prolonged outdoor exertion.",
        )
    elif aqi <= 300:
        return (
            "Poor",
            "#e74c3c",
            "Breathing discomfort to most people on prolonged exposure.",
            "Wear N95 masks outdoors; avoid strenuous workouts.",
        )
    elif aqi <= 400:
        return (
            "Very Poor",
            "#8e44ad",
            "Respiratory illness on prolonged exposure.",
            "Keep windows shut; run air purifiers indoors.",
        )
    else:
        return (
            "Severe",
            "#7f1d1d",
            "Affects healthy people and severely impacts those with existing diseases.",
            "Emergency conditions: stay indoors; strictly avoid outdoor exposure.",
        )


@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "Air Quality Index Microservice",
        "version": "1.0.0",
    }


@app.post("/api/v1/aqi/calculate", response_model=AQIResponseSchema)
def calculate_aqi(payload: SensorInputSchema):
    sub_indices = {
        "PM2.5": round(compute_sub_index(payload.pm25, BREAKPOINTS["PM2.5"]), 1),
        "PM10": round(compute_sub_index(payload.pm10, BREAKPOINTS["PM10"]), 1),
        "NO2": round(compute_sub_index(payload.no2, BREAKPOINTS["NO2"]), 1),
        "SO2": round(compute_sub_index(payload.so2, BREAKPOINTS["SO2"]), 1),
        "CO": round(compute_sub_index(payload.co, BREAKPOINTS["CO"]), 1),
    }

    dominant_pollutant = max(sub_indices, key=sub_indices.get)
    overall_aqi = max(sub_indices.values())
    category, color_hex, advisory, guidance = evaluate_category(overall_aqi)

    return AQIResponseSchema(
        overall_aqi=round(overall_aqi, 1),
        category=category,
        dominant_pollutant=dominant_pollutant,
        sub_indices=sub_indices,
        color_hex=color_hex,
        health_advisory=advisory,
        actionable_guidance=guidance,
    )


@app.get("/api/v1/dataset/summary")
def get_dataset_summary():
    try:
        df = pd.read_csv("air_quality_dataset.csv")
        return {
            "total_records": len(df),
            "means": df.mean().round(2).to_dict(),
            "medians": df.median().round(2).to_dict(),
            "maxs": df.max().round(2).to_dict(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Dataset reading error: {str(e)}"
        )