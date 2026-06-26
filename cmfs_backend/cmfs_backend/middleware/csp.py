class CSPMiddleware:
    POLICY = (
        "default-src 'self'; "#only load resources from from the same domain
        "script-src 'self'; "#s can only be loaded from your own server, locks inline<script> and external js
        "style-src 'self' 'unsafe-inline'; "#css is fine and inlinestyles allowed
        "img-src 'self' data:; "#images from your own server plus data: images like QR codes
        "font-src 'self'; "#fonts from your own server
        "connect-src 'self'; "
        "frame-ancestors 'none';"#no website can embed your pages in an <iframe>. Prevents clickjacking attacks.
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Content-Security-Policy'] = self.POLICY
        response['X-Content-Type-Options'] = 'nosniff'#stops the browser from guessing the file type. If the server says something is a text file, the browser must treat it as a text file, not execute it as JavaScript.
        response['X-Frame-Options'] = 'DENY'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'#when a user clicks a link to an external site, the browser only sends your domain name as the referrer, not the full URL path 
        return response