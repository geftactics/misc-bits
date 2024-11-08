# Rough POC showing how to authenticate with a MIFARE Ultralight-C card (MF0ICU2)
# Make sure that byte 0 of block 0x02 is set to 0x10 to require authentication for blocks above 0x10
# This script will perform authentication using the default key, and write 0xDE 0xAD 0xBE 0xEF to 0x20
# It will also print out all data blocks afterwards.

from smartcard.CardType import ATRCardType
from smartcard.CardRequest import CardRequest
from smartcard.util import toHexString
from Crypto.Cipher import DES3
import secrets

# Default MIFARE Ultralight-C keys
KEY1 = "49454D4B41455242" 
KEY2 = "214E4143554F5946"
TEST_WRITE_DATA = [0xDE, 0xAD, 0xBE, 0xEF]


def to_hex(byte_array):
    return toHexString(list(byte_array))

def send_apdu(cardservice, apdu):
    response, sw1, sw2 = cardservice.connection.transmit(apdu)
    if sw1 != 0x90 or sw2 != 0x00:
        raise ValueError(f"Bad response! sw1={sw1:02X}, sw2={sw2:02X}, data={to_hex(apdu)}")
    return response

def send_transparent_apdu(cardservice, data):
    # Transparent exchange APDU construction (See ACR1552U ref guide)
    length = len(data)
    apdu = [0xFF, 0xC2, 0x00, 0x01, length + 2, 0x95, length] + data
    response = send_apdu(cardservice, apdu)
    return bytes(response[14:])

def rotate_left(data, n=1):
    return data[n:] + data[:n]

def decrypt_des3(data, key, iv):
    cipher_dec = DES3.new(key + key[:8], DES3.MODE_CBC, iv)
    return cipher_dec.decrypt(data)

def encrypt_des3(data, key, iv):
    cipher_enc = DES3.new(key + key[:8], DES3.MODE_CBC, iv)
    return cipher_enc.encrypt(data)

def authenticate(cardservice):
    print("Starting authentication process...")
    
    # Send Authenticate APDU and retrieve encrypted RndB
    encRndB = send_transparent_apdu(cardservice, [0x1A, 0x00])[1:]
    print(" - Encrypted RndB:", to_hex(encRndB))

    # Decrypt RndB and generate RndA
    key = bytes.fromhex(KEY1 + KEY2)
    rndB = decrypt_des3(encRndB, key, iv=b'\x00' * 8)
    rndA = secrets.token_bytes(8)
    print(" - Decrypted RndB:", to_hex(rndB))
    print(" - Generated RndA:", to_hex(rndA))

    # Rotate and concatenate RndA and RndB
    rndB_rot = rotate_left(rndB)
    rndA_rndB_rot = rndA + rndB_rot
    print(" - RndA+RndB_rot:", to_hex(rndA_rndB_rot))

    # Encrypt concatenated RndA and RndB_rot
    encRndA_rndB_rot = encrypt_des3(rndA_rndB_rot, key, iv=encRndB)
    response_to_card = [0xAF] + list(encRndA_rndB_rot)
    encRndA = send_transparent_apdu(cardservice, response_to_card)[1:]
    print(" - Encrypted RndA Response:", to_hex(encRndA))

    # Verify RndA by decryption and rotation
    iv = encRndA_rndB_rot[-8:]
    rndA_prime = decrypt_des3(encRndA, key, iv=iv)
    if rndA_prime == rotate_left(rndA):
        print("Authentication successful: RndA matches")
    else:
        raise ValueError("Authentication failed: RndA does not match")

def read_all_blocks(cardservice):
    print("Reading all blocks:")
    for block in range(0x00, 0x2c):
        block_data = send_transparent_apdu(cardservice, [0x30, block])[:4]
        print(f" - [0x{block:02X}]: {to_hex(block_data)}")

def main():
    # Setup card connection
    cardtype = ATRCardType(bytes.fromhex("3B 8F 80 01 80 4F 0C A0 00 00 03 06 03 00 3A 00 00 00 00 51"))
    cardrequest = CardRequest(timeout=10, cardType=cardtype)
    cardservice = cardrequest.waitforcard()
    cardservice.connection.connect()

    # Start transparent session + ISO 14443-4A Active
    send_apdu(cardservice, [0xFF, 0xC2, 0x00, 0x00, 0x02, 0x81, 0x00])
    send_apdu(cardservice, [0xFF, 0xC2, 0x00, 0x02, 0x04, 0x8F, 0x02, 0x00, 0x03])

    # Authenticate
    authenticate(cardservice)

    # Write to block 0x20 and confirm by reading
    print("Writing to and reading from Block 0x20...")
    send_transparent_apdu(cardservice, [0xA2, 0x20] + TEST_WRITE_DATA)
    block_data = send_transparent_apdu(cardservice, [0x30, 0x20])[:4]
    print(f" - Data from Block 0x20: {to_hex(block_data)}")

    # Read all blocks
    read_all_blocks(cardservice)

    # End session
    send_apdu(cardservice, [0xFF, 0xC2, 0x00, 0x00, 0x02, 0x82, 0x00])

if __name__ == "__main__":
    main()
