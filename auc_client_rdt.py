"""
Authors
1. Ashvin Shivram Gaonkar (agaonka2)
2. Daksh Mehta (dmehta4)

Date - 20 November 2022
"""

# Import required libraries
import socket
import argparse
import time
import os
import numpy as np

# Define global variables
SIZE = 1024
FORMAT = "utf-8"
SERVER_BUSY = "Server is busy. Try to connect again later."
SELLER_ROLE = "Your role is: [Seller] \nPlease submit auction request:"
BUYER_ROLE = "Your role is: [Buyer]"
INVALID_REQUEST = "Invalid Request Information"
BID_ONGOING = "Bidding on-going!"


# Create client socket and connect to server Port Number


def createClientSocket(args):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((args.clientIP, args.hostPort))
    return client

# Get the arguments from command line


def get_command_line_arguments():
    parser = argparse.ArgumentParser('Auctioneer')
    parser.add_argument('clientIP', type=str, help='Host IP Number')
    parser.add_argument('hostPort', type=int, help='Host PORT Number')
    parser.add_argument('rdtPort', type=int, help='rdt PORT Number')
    parser.add_argument('rate', type=float, help='rate')
    args = parser.parse_args()
    return args

# Function to extract type of message received


def extract_type(msg):
    return int(msg.split(';{{}};')[1])

# Function to extract sequence of message received


def extract_seq(msg):
    return int(msg.split(';{{}};')[2])

# Function to extract data part of message received


def extract_data(msg):
    return msg.split(';{{}};')[0]

# Function to rectify the ack sent for printing


def rectify(a):
    if a == 1:
        return 0
    else:
        return 1

# Function to create a packet given msg, msg type, and sequence


def create_packet(msg, msg_type, seq):
    return str(msg)+';{{}};'+str(msg_type)+';{{}};'+str(seq)


def main():
    args = get_command_line_arguments()
    rate = 1 - args.rate
    client = createClientSocket(args)
    print('Connected to the Auctioneer server')
    connected = True
    while connected:
        serverWelcomeMessage = client.recv(SIZE).decode(FORMAT)
        # Server will send welcome prompt and based on that client can connect
        print(serverWelcomeMessage)
        # This is the stage where Seller have not completed the auction request to Server
        if serverWelcomeMessage == SERVER_BUSY:
            connected = False
            client.close()
        if serverWelcomeMessage == SELLER_ROLE:  # This is the first client. i.e. Seller
            bidInfo = input("Enter Bid Information: ")
            # Sends the auction request to Server
            client.send(bidInfo.encode(FORMAT))
            # Wait for feedback from Server i.e. data validation feedback
            reply = client.recv(SIZE).decode(FORMAT)
            print(reply)
            if reply == INVALID_REQUEST:  # If invalid auction request. Continue unitl Seller sends valid requests
                continue
            else:
                # Waiting for Server Auction Start Prompt.
                reply2 = client.recv(SIZE).decode(FORMAT)
                print(reply2)
                ########################################################
                winnderADDRandRDT = client.recv(SIZE).decode(FORMAT)
                IP, WINNER_RDT = winnderADDRandRDT.split(";")
                IP = IP.split(",")[0]
                IP = str(IP[2:-1])
                WINNER_RDT = int(WINNER_RDT)  # RDT Port number
                addrPart2 = (IP, WINNER_RDT)
                serverPart2 = socket.socket(
                    socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket
                print("UDP socket opened for RDT")
                file_name = "tosend.file"
                global file_size
                # size of file tosend.file
                file_size = str(os.path.getsize(file_name))
                lst = []
                size = []
                # reads the file in 2000 byte chunks and stores in buffer lst
                with open(file_name, "rb") as file:
                    size = 0
                    while size <= int(file_size):
                        data = file.read(2000)
                        if (not data):
                            break
                        lst.append(data)
                size = [0]*len(lst)
                size[0] = len(lst[0])
                for i in range(1, len(lst)):
                    size[i] = size[i-1]+len(lst[i])
                flag2 = 0
                i = -1
                seq = 0
                imp = None
                print('Start sending file.')
                while True:  # RDT Starts
                    if (i == -1):  # Taking care of control sequence start x
                        flag2 = 1
                        X = file_size
                        msg = f'start {X}'
                        print('Sending control seq', seq, ':', msg)
                        msg = create_packet(msg, 0, seq)
                        serverPart2.sendto(msg.encode('utf-8'), addrPart2)
                        time.sleep(0.02)
                    elif i == len(lst):  # Taking care of control sequence fin
                        msg = 'fin'
                        msg = create_packet(msg, 0, seq)
                        print('Sending control seq', seq)
                        serverPart2.sendto(msg.encode('utf-8'), addrPart2)
                        imp = True
                    elif i < int(file_size):  # sending data bytes
                        # print('i value:', i)
                        data = lst[i]
                        # print('sending - ', data)
                        print('Sending data seq', seq,
                              ':', size[i], '/', file_size)
                        msg = create_packet(data, 1, seq)
                        serverPart2.sendto(msg.encode('utf-8'), addrPart2)
                    # updating sequence number after sending to tackle duplicates
                    seq = 1 if seq == 0 else 0
                    # If no response in 2 seconds then timeout and drop packet
                    serverPart2.settimeout(2)
                    try:
                        ack = int(serverPart2.recv(2000).decode('utf-8'))
                        if ((np.random.binomial(n=1, p=rate)) == 1):  # TO simulate lossy network
                            if (ack == seq):  # correct ack received
                                print('Ack received : ', rectify(ack))
                                i += 1
                                print()
                            else:  # wrong ack received
                                seq = 1 if seq == 0 else 0
                                print(
                                    'Out of order ack; resending the packet with sequence:', seq)
                        elif (imp != True):
                            seq = 1 if seq == 0 else 0
                            print('Ack dropped: ', rectify(ack))
                            print()
                            continue
                        else:
                            print('Ack received : ', rectify(ack))
                            i += 1
                            print()

                    except:  # Timeout print statement
                        seq = 1 if seq == 0 else 0
                        print('Timeout; resending the packet with sequence:', seq)
                        continue

                    if i == len(lst)+1:  # File completely sent
                        print()
                        break

                ########################################################
                connected = False
                client.close()
        if serverWelcomeMessage == BUYER_ROLE:  # Client connect as buyer
            # Buyer receives minimum price for item from server
            minBidAmount = int(client.recv(SIZE).decode(FORMAT))
            # Waiting for "waiting for other buyer" prompt
            rep = client.recv(SIZE).decode(FORMAT)
            print(rep)
            # Waiting for bidding start prompt
            rep2 = client.recv(SIZE).decode(FORMAT)
            print(rep2)
            print('')
            while (True):  # Bid Validation of Buyer
                try:
                    bidAmount = int(input('Please submit your bid: '))
                except:
                    print(
                        f"Invalid Bidding Amount. Amount should be a positive integer greater than {minBidAmount}")
                    continue
                else:
                    while bidAmount < minBidAmount:
                        try:
                            print(
                                f"Invalid Bidding Amount. Amount should be a positive integer greater than {minBidAmount}")
                            bidAmount = int(input("Enter Bid Amount: "))
                        except:
                            continue
                    break
            client.send((str(bidAmount)+";"+str(args.rdtPort)
                         ).encode(FORMAT))  # Send bid to Server
            print('Bid received. Please wait...')
            # Buyer waiting for auction results.
            txt = client.recv(SIZE).decode(FORMAT)
            print(txt)
            ##################################################################
            txt = txt.split()
            if txt[3] == "won":
                transferStartTime = time.time()  # transfer start time
                clientPart2 = socket.socket(
                    socket.AF_INET, socket.SOCK_DGRAM)  # udp socket
                clientPart2.bind(("127.0.0.1", args.rdtPort))
                print("UDP Socket opened for RDT")
                print('Start receiving file')
                file_name = "recved.file"
                seq = 0
                flag = 0
                data = []
                counter = 0
                while True:  # RDT begins
                    if (flag == 0):
                        flag = 1
                        msg, connPart2 = clientPart2.recvfrom(10000)
                        msg = msg.decode('utf-8')
                        file_sizer = int(msg.split(';{{}};')[0].split()[1])
                        msg_type = extract_type(msg)
                        recv_seq = extract_seq(msg)
                        if (recv_seq == seq):
                            # receiving control message
                            print('Sequence Received:', recv_seq)
                            seq = 1 if seq == 0 else 0
                            ack = str(seq)
                            print('ACk sent:', rectify(int(ack)))
                            clientPart2.sendto(
                                ack.encode('utf-8'), connPart2)
                            print(extract_data(msg))
                        else:  # incorrect sequence number received
                            print('Msg received with mismatched sequence number',
                                  recv_seq, '. Expecting ', rectify(recv_seq))
                    else:
                        msg, connPart2 = clientPart2.recvfrom(10000)
                        if ((np.random.binomial(n=1, p=rate)) == 1):  # implementing lossy RDT
                            msg = msg.decode('utf-8')
                            msg_type = extract_type(msg)
                            recv_seq = extract_seq(msg)
                            if (recv_seq == seq):
                                # if control message fin then data transfer complete
                                if (extract_data(msg) == 'fin'):
                                    print('Msg received:', recv_seq)
                                    seq = 1 if seq == 0 else 0
                                    ack = str(seq)
                                    # send acknowledgment
                                    print('ACk sent:', rectify(int(ack)))
                                    print()
                                    clientPart2.sendto(
                                        ack.encode('utf-8'), connPart2)
                                    print('encountered fin')
                                    print('All Data Received! Exiting...')
                                    # clientPart2.close()
                                    break
                                else:
                                    temp = extract_data(msg)
                                    temp = temp[2:-1]
                                    temp = temp.encode('utf-8')
                                    c = temp.decode(
                                        'unicode-escape').encode('ISO-8859-1')
                                    # receive data and save in local buffer
                                    data.append(c)
                                    print('Msg received:', recv_seq)
                                    seq = 1 if seq == 0 else 0  # update sequence number to expect next packet
                                    ack = str(seq)
                                    print('ACk sent: ', rectify(int(ack)))
                                    counter += len(c)
                                    print('Received data seq', recv_seq,
                                          f': {counter} / {file_sizer}')
                                    print()
                                    clientPart2.sendto(
                                        ack.encode('utf-8'), connPart2)  # send acknowledgment
                            else:
                                # print(extract_data(msg))
                                clientPart2.sendto(
                                    str(seq).encode('utf-8'), connPart2)  # If incorrect packet sequence recvd
                                print('Out of order packet')
                                print()
                        else:
                            # In case the buyer drops the packet
                            print('PACKET DROPPED:', seq)
                            print()
                transferEndTime = time.time()  # stop transmission time
                transmissionCompleteTime = transferEndTime - transferStartTime
                averageThroughput = file_sizer / transmissionCompleteTime
                print(
                    f"Transmission finished: {file_sizer} bytes / {transmissionCompleteTime} = {averageThroughput} bps")
                with open("recved.file", "wb") as file:
                    for d in data:
                        file.write(d)  # writing to file from buffer

                clientPart2.close()  # close the socket
                connected = False
                break
            ###################################################################
            # Once the result is published connection is closed.
            else:
                connected = False
                client.close()

        # Handles if another Buyer tries to connect in middle of the on-going bidding.
        if serverWelcomeMessage == BID_ONGOING:
            connected = False
            client.close()


if __name__ == "__main__":
    main()
