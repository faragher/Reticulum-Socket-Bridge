import socket
import threading
import time
import RNS
import os

ipAddress = "127.0.0.1"
ipPort = 32198

targetIPPort = 32098

isListening = True

server_identity = None


## DEFINES
class CTL:
  ACK = b'\x06'
  NACK = b'\x15'


## SOCKET COMMUNICATION ROUTINES

# Barebones TCP to localhost. Could be UDP or any other standard, 
# this is not the point of the testbed. There is no error handling.
#
# Handing multi-packet communication, timing issues, and format
# are all the duty of the final application. These are all solved
# problems in TCP/IP, and are application and format specific.
#
# Thus this is designed to be sufficient to demonstrate.
# This is not acceptable for production use.

def SendPacket(data):
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as Client:
    Client.connect((ipAddress,targetIPPort))
    Client.sendall(data)
    ack=Client.recv(1)
  if(ack == CTL.ACK):
    print("Message acknowledged")
  elif(ack == CTL.NACK):
    print("Negatie Acknowledgement Received")
  else:
    print("Unhanded error. Not ACK/NACK")

def ServerLoop():
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as Server:
    Server.bind((ipAddress, ipPort))
    ListenThread = threading.Thread(target=Listen,args=(Server,))
    ListenThread.start()
    while True:
      time.sleep(250)
    ListenThread.join()

 
def Listen(Server):
  global isListening
  print("Listening")
  while(isListening):
    Server.listen()
    conn, addr = Server.accept()
    with conn:
      print(conn)
      conn.sendall(CTL.ACK)
      
## RETICULUM COMMUNICATION ROUTINES  
  
  
def InitReticulum():
  global server_identity
  path = os.path.expanduser("~")+"/.socket_test" # Where the program data lives
  reticulum = RNS.Reticulum() # Starts Reticulum w/ default config
  
  # Load path from configuration
  identitypath = path+"/storage/identity" # Identity location - can target any identity
  os.makedirs(path+"/storage",exist_ok=True) # Fails gracefully
  if os.path.exists(identitypath):
    server_identity = RNS.Identity.from_file(identitypath)
    print("Loaded identity")
  else:
    print("Making new identity")
    server_identity = RNS.Identity()
    server_identity.to_file(identitypath)
    
  # Set up destination
  # "socket_test" is the app_name and "requests" is the aspect. Using FQDN
  # this would look like requests.socket_test and functions similarly. For
  # example, adding more aspects could lead to foo.bar.requests.socket_test.
  # This works well for splitting up destinations in a logical manner, but
  # the finer points are beyond the scope of this program.
  #
  # Short version: the app_name and aspects MUST match or they won't see
  # each other and the connection will fail.
  server_destination = RNS.Destination(
    server_identity,
    RNS.Destination.IN,
    RNS.Destination.SINGLE,
    "socket_test", 
    "requests"
  )
  
  # Define Callbacks
  # Called when a link is established
  server_destination.set_link_established_callback(client_connected) 
  
  # Called when "Bridge" is requested. Will do so for ANY foreign user. Using 
  # allow=RNS.Destination.ALLOW_LIST with an "allowed_list =" argument will
  # only allow certain identities. See the core documentation or POPR for an example
  server_destination.register_request_handler("Bridge",response_generator = Bridge_Callback,allow = RNS.Destination.ALLOW_ALL)
  
  
# When a link is established, set the callback for identification
def client_connected(link):
    RNS.log("Client connected")
    link.set_remote_identified_callback(remote_identified)
  
def remote_identified(link, identity):
    RNS.log("Remote identified as: "+RNS.hexrep(identity.hash,delimit=""))
    # If you require any authentication, do it here. See POPR for an example.
    # With a single whitelist for both the request handler and this function,
    # you can control access with little effort.
    
# Bridging Callback
def Bridge_Callback(path,data,request_id,link_id,remote_identity,requested_at):
  if data:
    print(data)
    return CTL.ACK
  else:
    return CTL.NACK
    

# This is a TERRIBLE implementation. It makes many assumptions and is fragile.
# Do better than this.
def ParseRawMessage(data):
  dest = data[:16]
  message = data[16:]
  return dest, message
  
# Does the heavy lifting
def SendOverReticulum(destination_hash,payload):
      global server_identity
      # Check if we know the destination identity
      destination_identity = RNS.Identity.recall(destination_hash)
      # If we don't...
      if destination_identity == None:
        # ...start a timeout...
        basetime = time.time()
        # ...and query the network
        RNS.Transport.request_path(destination_hash)
        while destination_identity == None and (time.time() - basetime) < 30:
          destination_identity = RNS.Identity.recall(destination_hash)
          time.sleep(1)
      if destination_identity == None:
        print("Error: Cannot recall identity")
        return CTL.NACK
      print(RNS.hexrep(destination_identity.hash))
      # Set up a destination; name/aspects must match, but Destination.OUT
      remote_destination = RNS.Destination(
        destination_identity,
        RNS.Destination.OUT,
        RNS.Destination.SINGLE,
        "socket_test",
        "requests"
      )
      # Set up a link
      link = RNS.Link(remote_destination)
      # Wait until link is established
      basetime = time.time()
      while(link.status!=RNS.Link.ACTIVE and (time.time() - basetime) < 30):
        time.sleep(1)
      if(link.status != RNS.Link.ACTIVE):
        print("Link establishment timed out")
        return CTL.NACK
      # Identity this client (optional)
      link.identify(server_identity)
      # Send the request: Command, Payload, SuccessCallback, FailureCallback
      response = link.request(
        "Bridge",
        payload,
        EndLink,
        EndLink
      )
      print(response)
      return link
      
  
def EndLink(receipt):
  print("EndLink called")
  while(receipt.status < RNS.RequestReceipt.READY and receipt.status != RNS.RequestReceipt.FAILED):
    time.sleep(1)
  if(receipt.status == RNS.RequestReceipt.FAILED):
    print("Request failed.")
  else:
    print(receipt.response)
  receipt.link.teardown()
  
## PROGRAM

TestPacket =b'\x46\x6e\xa4\x35\x0d\x72\x80\xec\xa0\x78\x18\x33\xa1\x82\xb9\x69\xDE\xAD\xBE\xEF\xDE\xAD\xBE\xEF\xDE\xAD\xBE\xEF'
dest, message = ParseRawMessage(TestPacket)
print(dest)
print(message)
InitReticulum()
l = SendOverReticulum(dest,message)
while(l.status == RNS.Link.ACTIVE):
  time.sleep(1)
#SendPacket(b'\xDE\xAD\xBE\xEF')
#ServerLoop()

