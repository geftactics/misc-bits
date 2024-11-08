from smartcard.CardType import ATRCardType
from smartcard.CardRequest import CardRequest
from smartcard.util import toBytes, toHexString
from Crypto.Cipher import DES3
import binascii
import secrets

# Rough POC showing how to authenticate with a MIFARE Ultralight-C card (MF0ICU2)
# Works with an ACS ACR1552u USB reader
# Make sure that byte 0 of 0x2 is set to 0x10 to require authentication to blocks above 0x10
# This script will perform authentication using the default key, and write 0xDE 0xAD 0xBE 0xEF to 0x20
# It will also print out all data blocks afterwards.


KEY1 = "49454D4B41455242" # Default MIFARE Ultralight-C (BREAKMEIFYOUCAN!)
KEY2 = "214E4143554F5946"


def to_hex(byte_array):
    return binascii.hexlify(byte_array).decode().upper()

def read_all_blocks():
    print('Reading all data...')
    for block in range(0x00, 0x30):
        APDU = [0xFF, 0xC2, 0x00, 0x01, 0x04, 0x95, 0x02, 0x30, block]
        response, sw1, sw2 = cardservice.connection.transmit(APDU)
        block_data = response[14:18]
        print(f" - [0x{block:02X}]: {toHexString(block_data)}")




# Look for a MIFARE Ultralight-C ATR Card type...
cardtype = ATRCardType(toBytes("3B 8F 80 01 80 4F 0C A0 00 00 03 06 03 00 3A 00 00 00 00 51"))
cardrequest = CardRequest(timeout=10, cardType=cardtype)
cardservice = cardrequest.waitforcard()
cardservice.connection.connect()


# Start Transparent Session
APDU = [0xFF, 0xC2, 0x00, 0x00, 0x02, 0x81, 0x00]
response, sw1, sw2 = cardservice.connection.transmit(APDU)


# ISO 14443-4A Active
APDU = [0xFF, 0xC2, 0x00, 0x02, 0x04, 0x8F, 0x02, 0x00, 0x03]
response, sw1, sw2 = cardservice.connection.transmit(APDU)


# Start Authenticate
print("Start Authenticate...")
APDU = [0xFF, 0xC2, 0x00, 0x01, 0x04, 0x95, 0x02, 0x1A, 0x00]
response, sw1, sw2 = cardservice.connection.transmit(APDU)
if not (len(response) > 14 and response[14] == 0xAF):
    raise ValueError("Invalid response")
encRndB = bytes(response[15:23])
print(" - EncRndB:", encRndB.hex().upper())


# Decipher ek(RndB) to retrieve RndB
key = bytes.fromhex(KEY1 + KEY2)
iv = bytes.fromhex("0000000000000000")
cipher_dec = DES3.new(key + key[:8], DES3.MODE_CBC, iv)
rndB = cipher_dec.decrypt(encRndB)
print(" - Retrieved RndB:", to_hex(rndB))


# Generate RndA
rndA = secrets.token_bytes(8)
print(" - RndA:", to_hex(rndA))


# Rotate RndB left by 8 bits
rndB_rot = rndB[1:] + rndB[:1]
print(" - RndB_rot:", to_hex(rndB_rot))


# Concatenate
rndA_rndB_rot = rndA + rndB_rot
print(" - RndA+RndB:", to_hex(rndA_rndB_rot))


# Encrypt (RndA+RndB')
iv = encRndB
print(" - iv:", iv.hex().upper())
cipher_enc = DES3.new(key + key[:8], DES3.MODE_CBC, iv)
encRndA_rndB_rot = cipher_enc.encrypt(rndA_rndB_rot)
print(" - Enc(RndA+RndB):", to_hex(encRndA_rndB_rot))


# Response to send back to card (AF + Enc(RndA+RndB))
response_to_card = b'\xAF' + encRndA_rndB_rot
print("Response to Card:", to_hex(response_to_card))
APDU = [0xFF, 0xC2, 0x00, 0x01, 0x13, 0x95, len(response_to_card)] + list(response_to_card)
response, sw1, sw2 = cardservice.connection.transmit(APDU)
if not (len(response) > 22 and response[14] == 0x00):
    raise ValueError("Invalid response")
encRndA = bytes(response[15:23])
print(" - EncRndA:", encRndA.hex().upper())



# Final check
iv = encRndA_rndB_rot[-8:]
print(" - iv:", iv.hex().upper())
cipher_dec = DES3.new(key + key[:8], DES3.MODE_CBC, iv)
rndA_prime = cipher_dec.decrypt(encRndA)
print(" - Deciphered RndA:", to_hex(rndA_prime))
rndA_rot = rndA[1:] + rndA[:1]
print(" - RndA rotated:", to_hex(rndA_rot))

if rndA_prime == rndA_rot:
    print("Authentication successful: RndA matches")
else:
    raise ValueError("Authentication failed: RndA does not match")



# We have to use card specific write command as we are in transparent mode
print('Writing BLOCK 0x20...')
APDU = [0xFF, 0xC2, 0x00, 0x01, 0x08, 0x95, 0x06, 0xA2, 0x20, 0xDE, 0xAD, 0xBE, 0xEF]
response, sw1, sw2 = cardservice.connection.transmit(APDU)
print('Reading BLOCK 0x20...')
APDU = [0xFF, 0xC2, 0x00, 0x01, 0x04, 0x95, 0x02, 0x30, 0x20]
response, sw1, sw2 = cardservice.connection.transmit(APDU)
block_data = bytes(response[14:18]) # function returns 16 bytes
print(f" - Data: {block_data.hex().upper()}")


read_all_blocks()


# End Transparent Session
APDU = [0xFF, 0xC2, 0x00, 0x00, 0x02, 0x82, 0x00]
response, sw1, sw2 = cardservice.connection.transmit(APDU)
