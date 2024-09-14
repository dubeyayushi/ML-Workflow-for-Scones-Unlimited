""" The first lambda function is responsible for data generation.
SerializeImageData:
A lambda function that copies an object from S3, base64 encodes it, and 
then return it (serialized data) to the step function as `image_data` in an event.
"""

import json
import boto3
import base64
# import botocore

s3 = boto3.client('s3')

def lambda_handler(event, context):
    """A function to serialize target data from S3"""
    
    # Get the s3 address from the Step Function event input
    key = event["s3_key"] ## TODO: fill in
    bucket = event["s3_bucket"] ## TODO: fill in
    
    # Download the data from s3 to /tmp/image.png
    ## TODO: fill in
    boto3.resource('s3').Bucket(bucket).download_file(key, "/tmp/image.png")
    
    # We read the data from a file
    with open("/tmp/image.png", "rb") as f:
        image_data = base64.b64encode(f.read())

    # Pass the data back to the Step Function
    print("Event:", event.keys())
    return {
        'statusCode': 200,
        'body': {
            "image_data": image_data,
            "s3_bucket": bucket,
            "s3_key": key,
            "inferences": []
        }
    }


"""Test Event: 

{
  "s3_key": "test/bicycle_s_000513.png",
  "s3_bucket": "sagemaker-us-east-1-347758605116"
}

"""

""" The second one is responsible for image classification.
It takes the image output from the lambda 1 function(SerializeImageData), decodes it, and then pass inferences back to the the Step Function.
"""

import os
import io
import boto3
import json
import base64
# import sagemaker
# from sagemaker.serializers import IdentitySerializer


# setting the  environment variables
ENDPOINT_NAME = 'image-classification-2024-09-14-14-21-49-516'
# # We will be using the AWS's lightweight runtime solution to invoke an endpoint.
runtime= boto3.client('runtime.sagemaker')

def lambda_handler(event, context):

    # # Decode the image data
    image = base64.b64decode(event["body"]["image_data"])
    
    # Make a prediction:
    predictor = runtime.invoke_endpoint(EndpointName=ENDPOINT_NAME,
                                    #   ContentType='image/png',
                                    ContentType='application/x-image',
                                      Body=image)
    
    # We return the data back to the Step Function    
    event["inferences"] = json.loads(predictor['Body'].read().decode('utf-8'))
    return {
        'statusCode': 200,
        # 'body': json.dumps(event)
        "body": {
            "image_data": event["body"]['image_data'],
            "s3_bucket": event["body"]['s3_bucket'],
            "s3_key": event["body"]['s3_key'],
            "inferences": event['inferences'],
       }
    }


"""Test Event: 

{
  "statusCode": 200,
  "body": {
    "image_data": "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",
    "s3_bucket": "sagemaker-us-east-1-347758605116",
    "s3_key": "test/bicycle_s_000513.png",
    "inferences": []
  }
}

"""


""" 
The third function is responsible for filtering out low-confidence inferences.
It takes the inferences from the Lambda 2 function output and filters low-confidence inferences
"above a certain threshold indicating success"
"""
 
 
import json


THRESHOLD = .9

def lambda_handler(event, context):
    # Get the inferences from the event
    inferences = event["body"]["inferences"]
    
    # Check if any values in any inferences are above THRESHOLD
    meets_threshold = (max(inferences) > THRESHOLD)
    
    # If our threshold is met, pass our data back out of the
    # Step Function, else, end the Step Function with an error
    if meets_threshold:
        pass
    else:
        raise("THRESHOLD_CONFIDENCE_NOT_MET")

    return {
        'statusCode': 200,
        'body': json.dumps(event)
    }

"""Test Event: 

{
  "body": {
    "image_data": "iVBORw0KGgoAAAANSUhEUgAAATYAAACeCAYAAAC4hCaeAAAMQGlDQ1BJQ0MgUHJvZmlsZQAASImVVwdYU8kWnluSkEBooUsJvQkiUgJICaEFkF4EUQlJgFBiDAQVe1lUcC2oiIINXRVR7DQLiigWFsXeFwsKyrpYsCtvUkDXfeV75/vm3v/+c+Y/Z86dWwYAtZMckSgHVQcgV5gvjgn2p49PSqaTegACdAEZUAGJw80TMaOiwgG0ofPf7d0N6A3tqoNU65/9/9U0ePw8LgBIFMRpvDxuLsSHAcAruSJxPgBEKW8+LV8kxbABLTFMEOIlUpwhx5VSnCbH+2U+cTEsiFsBUFLhcMQZAKhehjy9gJsBNVT7IXYS8gRCANToEPvk5k7hQZwKsQ30EUEs1Wek/aCT8TfNtGFNDidjGMvnIjOlAEGeKIcz4/8sx/+23BzJUAwr2FQyxSEx0jnDut3KnhImxSoQ9wnTIiIh1oT4g4An84cYpWRKQuLl/qghN48FawZ0IHbicQLCIDaEOEiYExGu4NPSBUFsiOEKQacL8tlxEOtBvISfFxir8NkinhKjiIXWpYtZTAV/jiOWxZXGeiDJjmcq9F9n8tkKfUy1MDMuEWIKxBYFgoQIiFUhdszLjg1T+IwtzGRFDPmIJTHS/C0gjuELg/3l+lhBujgoRuFfnJs3NF9sS6aAHaHAB/Mz40Lk9cFauRxZ/nAu2GW+kBk/pMPPGx8+NBcePyBQPneshy+Mj1XofBDl+8fIx+IUUU6Uwh834+cES3kziF3yCmIVY/GEfLgg5fp4uig/Kk6eJ16YxQmNkueDrwThgAUCAB1IYEsDU0AWEHT01ffBK3lPEOAAMcgAfOCgYIZGJMp6hPAYCwrBnxDxQd7wOH9ZLx8UQP7rMCs/OoB0WW+BbEQ2eApxLggDOfBaIhslHI6WAJ5ARvCP6BzYuDDfHNik/f+eH2K/M0zIhCsYyVBEutqQJzGQGEAMIQYRbXED3Af3wsPh0Q82Z5yBewzN47s/4Smhk/CIcJ3QRbg9WbBA/FOW40AX1A9S1CLtx1rgVlDTFffHvaE6VMZ1cAPggLvAOEzcF0Z2hSxLkbe0KvSftP82gx/uhsKP7ERGybpkP7LNzyNV7VRdh1Wktf6xPvJc04brzRru+Tk+64fq8+A57GdPbAl2CGvDTmHnsWNYPaBjzVgD1o4dl+Lh1fVEtrqGosXI8smGOoJ/xBu6s9JK5jnVOPU6fZH35fOnS9/RgDVFNEMsyMjMpzPhF4FPZwu5jiPpzk7OLgBIvy/y19ebaNl3A9Fp/84t/AMA7+bBwcGj37nQZgAOuMPHv/E7Z8OAnw5lAM41ciXiAjmHSw8E+JZQg0+aPjAG5sAGzscZuAEv4AcCQSiIBHEgCUyC2WfCdS4G08AsMB8UgRKwEqwFG8BmsA3sAnvBQVAPjoFT4Cy4CC6D6+AuXD3d4AXoB+/AZwRBSAgVoSH6iAliidgjzggD8UECkXAkBklCUpEMRIhIkFnIQqQEKUU2IFuRauQA0oicQs4jncht5CHSi7xGPqEYqoJqoUaoFToKZaBMNAyNQyeiGehUtBBdhC5Hy9EqdA9ah55CL6LX0S70BTqAAUwZ08FMMQeMgbGwSCwZS8fE2BysGCvDqrBarAne56tYF9aHfcSJOA2n4w5wBYfg8TgXn4rPwZfhG/BdeB3eil/FH+L9+DcClWBIsCd4EtiE8YQMwjRCEaGMsINwhHAGPkvdhHdEIlGHaE10h89iEjGLOJO4jLiRuI94kthJfEwcIJFI+iR7kjcpksQh5ZOKSOtJe0jNpCukbtIHJWUlEyVnpSClZCWh0gKlMqXdSieUrig9U/pMVidbkj3JkWQeeQZ5BXk7uYl8idxN/kzRoFhTvClxlCzKfEo5pZZyhnKP8kZZWdlM2UM5WlmgPE+5XHm/8jnlh8ofVTRV7FRYKikqEpXlKjtVTqrcVnlDpVKtqH7UZGo+dTm1mnqa+oD6QZWm6qjKVuWpzlWtUK1TvaL6Uo2sZqnGVJukVqhWpnZI7ZJanzpZ3Uqdpc5Rn6Neod6oflN9QIOmMVojUiNXY5nGbo3zGj2aJE0rzUBNnuYizW2apzUf0zCaOY1F49IW0rbTztC6tYha1lpsrSytEq29Wh1a/dqa2i7aCdrTtSu0j2t36WA6VjpsnRydFToHdW7ofNI10mXq8nWX6tbqXtF9rzdCz0+Pr1est0/vut4nfbp+oH62/ir9ev37BriBnUG0wTSDTQZnDPpGaI3wGsEdUTzi4Ig7hqihnWGM4UzDbYbthgNGxkbBRiKj9UanjfqMdYz9jLOM1xifMO41oZn4mAhM1pg0mzyna9OZ9Bx6Ob2V3m9qaBpiKjHdatph+tnM2izebIHZPrP75hRzhnm6+RrzFvN+CxOLcRazLGos7liSLRmWmZbrLNss31tZWyVaLbaqt+qx1rNmWxda11jfs6Ha+NpMtamyuWZLtGXYZttutL1sh9q52mXaVdhdskft3ewF9hvtO0cSRnqMFI6sGnnTQcWB6VDgUOPw0FHHMdxxgWO948tRFqOSR60a1Tbqm5OrU47Tdqe7ozVHh45eMLpp9GtnO2euc4XztTHUMUFj5o5pGPPKxd6F77LJ5ZYrzXWc62LXFtevbu5uYrdat153C/dU90r3mwwtRhRjGeOcB8HD32OuxzGPj55unvmeBz3/8nLwyvba7dUz1nosf+z2sY+9zbw53lu9u3zoPqk+W3y6fE19Ob5Vvo/8zP14fjv8njFtmVnMPcyX/k7+Yv8j/u9ZnqzZrJMBWEBwQHFAR6BmYHzghsAHQWZBGUE1Qf3BrsEzg0+GEELCQlaF3GQbsbnsanZ/qHvo7NDWMJWw2LANYY/C7cLF4U3j0HGh41aPuxdhGSGMqI8EkezI1ZH3o6yjpkYdjSZGR0VXRD+NGR0zK6YtlhY7OXZ37Ls4/7gVcXfjbeIl8S0JagkpCdUJ7xMDEksTu8aPGj97/MUkgyRBUkMyKTkheUfywITACWsndKe4phSl3JhoPXH6xPOTDCblTDo+WW0yZ/KhVEJqYuru1C+cSE4VZyCNnVaZ1s9lcddxX/D8eGt4vXxvfin/Wbp3eml6T4Z3xuqM3kzfzLLMPgFLsEHwKiska3PW++zI7J3ZgzmJOftylXJTcxuFmsJsYesU4ynTp3SK7EVFoq6pnlPXTu0Xh4l35CF5E/Ma8rXgj3y7xEbyi+RhgU9BRcGHaQnTDk3XmC6c3j7DbsbSGc8Kgwp/m4nP5M5smWU6a/6sh7OZs7fOQeakzWmZaz530dzuecHzds2nzM+e//sCpwWlC94uTFzYtMho0bxFj38J/qWmSLVIXHRzsdfizUvwJYIlHUvHLF2/9Fsxr/hCiVNJWcmXZdxlF34d/Wv5r4PL05d3rHBbsWklcaVw5Y1Vvqt2lWqUFpY+Xj1udd0a+priNW/XTl57vsylbPM6yjrJuq7y8PKG9RbrV67/siFzw/UK/4p9lYaVSyvfb+RtvLLJb1PtZqPNJZs/bRFsubU1eGtdlVVV2TbitoJtT7cnbG/7jfFb9Q6DHSU7vu4U7uzaFbOrtdq9unq34e4VNWiNpKZ3T8qey3sD9jbUOtRu3aezr2Q/2C/Z//xA6oEbB8MOthxiHKo9bHm48gjtSHEdUjejrr8+s76rIamhszG0saXJq+nIUcejO4+ZHqs4rn18xQnKiUUnBpsLmwdOik72nco49bhlcsvd0+NPX2uNbu04E3bm3Nmgs6fbmG3N57zPHTvveb7xAuNC/UW3i3Xtru1Hfnf9/UiHW0fdJfdLDZc9Ljd1ju08ccX3yqmrAVfPXmNfu3g94nrnjfgbt26m3Oy6xbvVczvn9qs7BXc+3513j3Cv+L76/bIHhg+q/rD9Y1+XW9fxhwEP2x/FPrr7mPv4xZO8J1+6Fz2lPi17ZvKsuse551hvUO/l5xOed78QvfjcV/Snxp+VL21eHv7L76/2/vH93a/ErwZfL3uj/2bnW5e3LQNRAw/e5b77/L74g/6HXR8ZH9s+JX569nnaF9KX8q+2X5u+hX27N5g7OCjiiDmyXwEMNjQ9HYDXOwGgJgFAg/szygT5/k9miHzPKkPgP2H5HlFmbgDUwv/36D74d3MTgP3b4fYL6qulABBFBSDOA6Bjxgy3ob2abF8pNSLcB2xhf03LTQP/xuR7zh/y/vkMpKou4OfzvwDG63w6vS06lgAAAIplWElmTU0AKgAAAAgABAEaAAUAAAABAAAAPgEbAAUAAAABAAAARgEoAAMAAAABAAIAAIdpAAQAAAABAAAATgAAAAAAAACQAAAAAQAAAJAAAAABAAOShgAHAAAAEgAAAHigAgAEAAAAAQAAATagAwAEAAAAAQAAAJ4AAAAAQVNDSUkAAABTY3JlZW5zaG90s1I/+QAAAAlwSFlzAAAWJQAAFiUBSVIk8AAAAdZpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IlhNUCBDb3JlIDYuMC4wIj4KICAgPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4KICAgICAgPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIKICAgICAgICAgICAgeG1sbnM6ZXhpZj0iaHR0cDovL25zLmFkb2JlLmNvbS9leGlmLzEuMC8iPgogICAgICAgICA8ZXhpZjpQaXhlbFlEaW1lbnNpb24+MTU4PC9leGlmOlBpeGVsWURpbWVuc2lvbj4KICAgICAgICAgPGV4aWY6UGl4ZWxYRGltZW5zaW9uPjMxMDwvZXhpZjpQaXhlbFhEaW1lbnNpb24+CiAgICAgICAgIDxleGlmOlVzZXJDb21tZW50PlNjcmVlbnNob3Q8L2V4aWY6VXNlckNvbW1lbnQ+CiAgICAgIDwvcmRmOkRlc2NyaXB0aW9uPgogICA8L3JkZjpSREY+CjwveDp4bXBtZXRhPgqA0oy4AAAAHGlET1QAAAACAAAAAAAAAE8AAAAoAAAATwAAAE8AAAKUvhXXpQAAAmBJREFUeAHs1AENACAMA0HmXzQjyPjcHOzadO674wgQIBASGMMWStMrBAh8AcOmCAQI5AQMWy5SDxEgYNh0gACBnIBhy0XqIQIEDJsOECCQEzBsuUg9RICAYdMBAgRyAoYtF6mHCBAwbDpAgEBOwLDlIvUQAQKGTQcIEMgJGLZcpB4iQMCw6QABAjkBw5aL1EMECBg2HSBAICdg2HKReogAAcOmAwQI5AQMWy5SDxEgYNh0gACBnIBhy0XqIQIEDJsOECCQEzBsuUg9RICAYdMBAgRyAoYtF6mHCBAwbDpAgEBOwLDlIvUQAQKGTQcIEMgJGLZcpB4iQMCw6QABAjkBw5aL1EMECBg2HSBAICdg2HKReogAAcOmAwQI5AQMWy5SDxEgYNh0gACBnIBhy0XqIQIEDJsOECCQEzBsuUg9RICAYdMBAgRyAoYtF6mHCBAwbDpAgEBOwLDlIvUQAQKGTQcIEMgJGLZcpB4iQMCw6QABAjkBw5aL1EMECBg2HSBAICdg2HKReogAAcOmAwQI5AQMWy5SDxEgYNh0gACBnIBhy0XqIQIEDJsOECCQEzBsuUg9RICAYdMBAgRyAoYtF6mHCBAwbDpAgEBOwLDlIvUQAQKGTQcIEMgJGLZcpB4iQMCw6QABAjkBw5aL1EMECBg2HSBAICdg2HKReogAAcOmAwQI5AQMWy5SDxEgYNh0gACBnIBhy0XqIQIEDJsOECCQEzBsuUg9RICAYdMBAgRyAoYtF6mHCBAwbDpAgEBOwLDlIvUQAQKGTQcIEMgJGLZcpB4iQMCw6QABAjmBBQAA///w5CPDAAACXklEQVTt1AENACAMA0HmXzQjyPjcHOzadO674wgQIBASGMMWStMrBAh8AcOmCAQI5AQMWy5SDxEgYNh0gACBnIBhy0XqIQIEDJsOECCQEzBsuUg9RICAYdMBAgRyAoYtF6mHCBAwbDpAgEBOwLDlIvUQAQKGTQcIEMgJGLZcpB4iQMCw6QABAjkBw5aL1EMECBg2HSBAICdg2HKReogAAcOmAwQI5AQMWy5SDxEgYNh0gACBnIBhy0XqIQIEDJsOECCQEzBsuUg9RICAYdMBAgRyAoYtF6mHCBAwbDpAgEBOwLDlIvUQAQKGTQcIEMgJGLZcpB4iQMCw6QABAjkBw5aL1EMECBg2HSBAICdg2HKReogAAcOmAwQI5AQMWy5SDxEgYNh0gACBnIBhy0XqIQIEDJsOECCQEzBsuUg9RICAYdMBAgRyAoYtF6mHCBAwbDpAgEBOwLDlIvUQAQKGTQcIEMgJGLZcpB4iQMCw6QABAjkBw5aL1EMECBg2HSBAICdg2HKReogAAcOmAwQI5AQMWy5SDxEgYNh0gACBnIBhy0XqIQIEDJsOECCQEzBsuUg9RICAYdMBAgRyAoYtF6mHCBAwbDpAgEBOwLDlIvUQAQKGTQcIEMgJGLZcpB4iQMCw6QABAjkBw5aL1EMECBg2HSBAICdg2HKReogAAcOmAwQI5AQMWy5SDxEgYNh0gACBnIBhy0XqIQIEDJsOECCQEzBsuUg9RICAYdMBAgRyAoYtF6mHCBAwbDpAgEBOwLDlIvUQAQKGTQcIEMgJGLZcpB4iQMCw6QABAjmBBYKHdkXJKXmzAAAAAElFTkSuQmCC",
    "s3_bucket": "sagemaker-us-east-1-347758605116",
    "s3_key": "test/bicycle_s_000513.png",
    "inferences": [0.95, 0.85, 0.7]
  }
}


"""


