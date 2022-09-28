def validate_x_request_url(x_request_url: str):
    """Doesn't match the required step signature!"""
    if x_request_url == "something":
        raise ValueError("Invalid value for 'x_request_url'")
