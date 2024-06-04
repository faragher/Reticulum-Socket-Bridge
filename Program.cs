using System;
using System.Net;
using System.Net.Sockets;

Main();

static int Main()
{
    Console.WriteLine("Program Start");
    RSB Bridge = new RSB();
    Bridge.Start();
    return 0;
}


// Reticulum Socket Bridge
public class RSB
{
    const int serverPort = 32098;
    const int remotePort = 32198;
    IPEndPoint localhost = new IPEndPoint(IPAddress.Loopback, serverPort);
    //public Socket server{ get; private set; }
    public TcpListener server { get; private set; }
    public bool isListening = true;

    public RSB()
    {
        server = new TcpListener(localhost);
    }

    public void Start()
    {
        Console.WriteLine("TCP Listener on " + localhost.Address + ":" + localhost.Port);
        server.Start();

        Console.WriteLine("Initializing server...");

        while (isListening)
        {
            if (Console.KeyAvailable && Console.ReadKey(true).Key == ConsoleKey.Escape)
            {
                isListening = false;
            }
            if (server.Pending())
            {
                Console.WriteLine("Beep");
                TcpClient TC = server.AcceptTcpClient();
                NetworkStream ns = TC.GetStream();
                int size = TC.Available;
                byte[] buffer = new byte[size];
                int bytesRead = ns.Read(buffer, 0, size);
                for(int i = 0; i < bytesRead; i++)
                {
                    Console.WriteLine("{0:X2} ",buffer[i]);
                }
                byte[] buffer2 = {0x06};
                ns.Write(buffer2, 0, buffer2.Length);
                TC.Dispose();
            }
            Thread.Sleep(100);
        }
        server.Stop();
    }

    //public byte SendMessage(byte[] payload)
    //{

    //}
}


