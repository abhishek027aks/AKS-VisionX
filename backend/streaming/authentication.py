from rest_framework_simplejwt.authentication import JWTAuthentication


class QueryStringJWTAuthentication(JWTAuthentication):
    """
    Authenticate normal Bearer JWT headers and also allow
    a JWT supplied as ?token=... for browser MJPEG <img> requests.
    """

    def authenticate(self, request):
        header = self.get_header(request)

        if header is not None:
            raw_token = self.get_raw_token(header)
        else:
            token = request.query_params.get("token")

            if not token:
                return None

            raw_token = token.encode("utf-8")

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        return (
            self.get_user(validated_token),
            validated_token,
        )
