from smartcard.CardType import ATRCardType
from smartcard.CardRequest import CardRequest
from smartcard.util import toHexString
from Crypto.Cipher import DES3
import binascii
import secrets


# Rough POC showing how to authenticate with a MIFARE Ultralight-C card (MF0ICU2)
# Make sure that byte 0 of block 0x02 is set to 0x10 to require authentication for blocks above 0x10
# This script will perform authentication using the default key, and write 0xDE 0xAD 0xBE 0xEF to 0x20
# It will also print out all data blocks afterwards.


# Default MIFARE Ultralight-C keys
KEY1 = "49454D4B41455242" 
KEY2 = "214E4143554F5946"


def send_apdu(cardservice, apdu):
    response, sw1, sw2 = cardservice.connection.transmit(apdu)
    if sw1 != 0x90 and sw2 != 0x00:
        raise ValueError(f"Bad response! sw1={sw1:02X}, sw2={sw2:02X}, data={to_hex(bytes(apdu))}")
    return response


def send_transparent_apdu(cardservice, data):
    # Transparent exchange (6.2.7) in ACR1552U reference manual
    length = len(data) 
    apdu = [0xFF, 0xC2, 0x00, 0x01] + [length+2] + [0x95] + [length] + data
    response, sw1, sw2 = cardservice.connection.transmit(apdu)
    if sw1 != 0x90 and sw2 != 0x00:
        raise ValueError(f"Bad response! sw1={sw1:02X}, sw2={sw2:02X}, data={to_hex(bytes(data))}")
    return bytes(response[14:])

def read_all_blocks():
    print('Reading all data...')
    for block in range(0x00, 0x2c):
        block_data = send_transparent_apdu(cardservice, [0x30, block])[:4]
        print(f" - [0x{block:02X}]: {to_hex(block_data)}")


def to_hex(byte_array):
    return toHexString(list(byte_array))


# Look for a MIFARE Ultralight-C ATR Card type...
cardtype = ATRCardType(bytes.fromhex("3B 8F 80 01 80 4F 0C A0 00 00 03 06 03 00 3A 00 00 00 00 51"))
cardrequest = CardRequest(timeout=10, cardType=cardtype)
cardservice = cardrequest.waitforcard()
cardservice.connection.connect()


# Transparent session and ISO 14443-4A Active
send_apdu(cardservice, [0xFF, 0xC2, 0x00, 0x00, 0x02, 0x81, 0x00])
send_apdu(cardservice, [0xFF, 0xC2, 0x00, 0x02, 0x04, 0x8F, 0x02, 0x00, 0x03])


# Start Authenticate
encRndB = send_transparent_apdu(cardservice, [0x1A, 0x00])[1:]
print(" - EncRndB:", to_hex(encRndB))


# Decipher ek(RndB) to retrieve RndB
key = bytes.fromhex(KEY1 + KEY2)
iv = bytes.fromhex("0000000000000000")
cipher_dec = DES3.new(key + key[:8], DES3.MODE_CBC, iv)
rndB = cipher_dec.decrypt(encRndB)
print(" - RndB:", to_hex(rndB))


# Generate RndA
rndA = secrets.token_bytes(8)
print(" - RndA:", to_hex(rndA))


# Rotate RndB left by 8 bits
rndB_rot = rndB[1:] + rndB[:1]
print(" - RndB_rot:", to_hex(rndB_rot))


# Concatenate
rndA_rndB_rot = rndA + rndB_rot
print(" - RndA+RndB_rot:", to_hex(rndA_rndB_rot))


# Encrypt (RndA+RndB)
iv = encRndB
cipher_enc = DES3.new(key + key[:8], DES3.MODE_CBC, iv)
encRndA_rndB_rot = cipher_enc.encrypt(rndA_rndB_rot)
print(" - iv:", to_hex(iv))
print(" - Enc(RndA+RndB):", to_hex(encRndA_rndB_rot))


# Response to send back to card (0xAF + Enc(RndA+RndB))
response_to_card = [0xAF] + list(encRndA_rndB_rot)
encRndA = send_transparent_apdu(cardservice, response_to_card)[1:]
print("Response to Card:", to_hex(response_to_card))
print(" - EncRndA:", to_hex(encRndA))


# Final check
iv = encRndA_rndB_rot[-8:]
cipher_dec = DES3.new(key + key[:8], DES3.MODE_CBC, iv)
rndA_prime = cipher_dec.decrypt(encRndA)
rndA_rot = rndA[1:] + rndA[:1]
print(" - iv:", to_hex(iv))
print(" - Deciphered RndA:", to_hex(rndA_prime))
print(" - RndA rotated:", to_hex(rndA_rot))

if rndA_prime == rndA_rot:
    print("Authentication successful: RndA matches")
else:
    raise ValueError("Authentication failed: RndA does not match")


# Confirm authentication by writing to 0x20
print('Writing BLOCK 0x20...')
APDU_CMD = [0xA2, 0x20]
data = [0xDE, 0xAD, 0xBE, 0xEF]
send_transparent_apdu(cardservice, APDU_CMD + data)


# Confirm authentication by reading from 0x20
print('Reading BLOCK 0x20...')
APDU_CMD = [0x30, 0x20]
block_data = send_transparent_apdu(cardservice, APDU_CMD)[:4]
print(f" - Data: {to_hex(block_data)}")

read_all_blocks()

# End Transparent Session
send_apdu(cardservice, [0xFF, 0xC2, 0x00, 0x00, 0x02, 0x82, 0x00])
