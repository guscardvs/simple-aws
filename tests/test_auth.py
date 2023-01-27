from datetime import datetime
from datetime import timezone

from simple_aws.auth import AwsAuthV4
from simple_aws.credentials import Credentials

now = datetime.fromisoformat("2013-05-24T00:00:00")
now.replace(tzinfo=timezone.utc)


def test_aws_auth_returns_expected_result_get_case(credential: Credentials):
    expected = (
        "AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/20130524/us-east-1/"
        "s3/aws4_request,SignedHeaders=host;range;x-amz-content-sha256;"
        "x-amz-date,Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"
    )
    aws_auth_v4 = AwsAuthV4(credential, "s3")
    headers = aws_auth_v4.headers(
        "GET",
        "https://examplebucket.s3.amazonaws.com/test.txt",
        now=now,
        headers={"range": "bytes=0-9"},
    )
    assert headers["authorization"] == expected


def test_aws_auth_returns_expected_result_get_lifecycle_case(
    credential: Credentials,
):
    expected = (
        "AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/20130524/us-east-1/s3"
        "/aws4_request,SignedHeaders=host;x-amz-content-sha256;"
        "x-amz-date,Signature=fea454ca298b7da1c68078a5d1bdbfbbe0d65c699e0f91ac7a200a0136783543"
    )
    aws_auth_v4 = AwsAuthV4(credential, "s3")
    headers = aws_auth_v4.headers(
        "GET",
        "https://examplebucket.s3.amazonaws.com/?lifecycle",
        now=now,
    )
    assert headers["authorization"] == expected


def test_aws_auth_returns_expected_result_put_object_case(
    credential: Credentials,
):
    expected = (
        "AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/20130524/us-east-1/"
        "s3/aws4_request,SignedHeaders=date;host;x-amz-content-sha256;"
        "x-amz-date;x-amz-storage-class,"
        "Signature=98ad721746da40c64f1a55b78f14c238d841ea1380cd77a1b5971af0ece108bd"
    )
    aws_auth_v4 = AwsAuthV4(credential, "s3", use_default_headers=False)
    body = "Welcome to Amazon S3.".encode()
    headers = aws_auth_v4.headers(
        "PUT",
        "https://examplebucket.s3.amazonaws.com/test$file.text",
        now=now,
        headers={
            "date": "Fri, 24 May 2013 00:00:00 GMT",
            "x-amz-storage-class": "REDUCED_REDUNDANCY",
        },
        data=body,
    )
    assert headers["authorization"] == expected


def test_aws_auth_returns_expected_result_list_object_case(
    credential: Credentials,
):
    expected = (
        "AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/20130524/us-east-1/"
        "s3/aws4_request,SignedHeaders=host;x-amz-content-sha256;x-amz-date,"
        "Signature=34b48302e7b5fa45bde8084f4b7868a86f0a534bc59db6670ed5711ef69dc6f7"
    )
    aws_awth_v4 = AwsAuthV4(credential, "s3")
    headers = aws_awth_v4.headers(
        "GET",
        "https://examplebucket.s3.amazonaws.com/?max-keys=2&prefix=J",
        now=now,
    )
    assert headers["authorization"] == expected
