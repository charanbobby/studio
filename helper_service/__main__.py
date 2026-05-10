import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "helper_service.api:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
