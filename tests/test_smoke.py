def test_app_imports():
    import main
    # we expect your FastAPI app to live in main.app
    assert hasattr(main, "app")
