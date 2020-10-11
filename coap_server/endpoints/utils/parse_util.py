def parse_post_data(request_payload):
    """
    Decodes the payload into an ASCII string then parses the POST data and
    variables into a dictionary where the keys are the variable names from the
    POST request.

    Parameters:
        request_payload:
            the POST request payload that is encoded ASCII

    Returns:
        a dictionary representing the variables from the POST request
    """
    data = request_payload.decode('ascii').split('&')
    return {param[:param.find('=')] : param[param.find('=') + 1:] for param in data}
