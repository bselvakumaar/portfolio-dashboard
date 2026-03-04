import argparse

from cryptography.fernet import Fernet


def main() -> None:
    parser = argparse.ArgumentParser(description="Encrypt a secret for .env usage")
    parser.add_argument("--value", required=True, help="Plain secret value")
    parser.add_argument(
        "--key",
        default="",
        help="Existing Fernet key. If omitted, a new key is generated.",
    )
    args = parser.parse_args()

    key = args.key.encode("utf-8") if args.key else Fernet.generate_key()
    cipher = Fernet(key)
    encrypted = cipher.encrypt(args.value.encode("utf-8"))

    print("APP_ENCRYPTION_KEY=" + key.decode("utf-8"))
    print("TRADING_DATABASE_URL_ENCRYPTED=" + encrypted.decode("utf-8"))


if __name__ == "__main__":
    main()
