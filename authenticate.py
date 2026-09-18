from pydrive2.auth import GoogleAuth

print("Starting authentication...")
gauth = GoogleAuth()
print("Opening browser for authentication...")
gauth.LocalWebserverAuth()
gauth.SaveCredentialsFile('credentials.json')
print('\n=== Authentication successful! ===')
print('credentials.json has been created')
