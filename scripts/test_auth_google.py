import requests


def main():
	r = requests.get('http://localhost:8000/api/auth/google', allow_redirects=False, timeout=10)
	print('status', r.status_code)
	print('location', r.headers.get('location'))


if __name__ == '__main__':
	main()
