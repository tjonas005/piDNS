from scapy.all import *
import random
nameDirectory = []
IPDirectory = []
ROOTNAMESERVER = '198.41.0.4'

def startup():
    networkLayer = IP(dst=ROOTNAMESERVER)
    transportLayer = UDP(dport=53, sport=56980)
    startpacket = networkLayer/transportLayer
    resp = sr1(startpacket, timeout = 1)






def getSiteIP(siteName, rd):
    global nameDirectory
    global IPDirectory
    siteIP = ""
    found = False

    #Kijk of de requested domain name in de opgeslaan lijst zit
    for i in range(len(nameDirectory)):
        if nameDirectory[i] == siteName:
            #wanneer deze in de lijst zit, zet het siteIP op de overeenkomstige IP opgeslaan in de lijst
            siteIP = IPDirectory[i]
            found = True


    #indien de domain name niet gevonden werd: query de backup server
    if not(found):
        TLDList = []
        networkLayer = IP(dst=ROOTNAMESERVER)
        transportLayer = UDP(dport=53, sport=56980)
        applicationLayer = DNS(id=random.randint(0, 10000), rd=1, qd=DNSQR(qname=siteName, qtype= 'A'))

        RNSquery = networkLayer/transportLayer/applicationLayer

        RNSresp = sr1(RNSquery, timeout=1)

        TLDList = []
        for i in range(RNSresp[DNS].arcount):
            if len(RNSresp[DNS].ar[i].rdata) < 15:
                TLDList.append(RNSresp[DNS].ar[i].rdata)
        i = 0
        ANS = None
        while ANS == None and i < len(TLDList):
            networkLayer = IP(dst=TLDList[i])
            i += 1

            transportLayer = UDP(dport=53, sport=56980)
            applicationLayer = DNS(id=random.randint(0, 10000), rd=1, qd=DNSQR(qname=siteName, qtype= 'NS'))

            TLDquery = networkLayer/transportLayer/applicationLayer

            TLDresp = sr1(TLDquery, timeout=1)

            if TLDresp[DNS].ar != None:
                ANS = TLDresp[DNS].ar[0].rdata


        if ANS == None:
            ANS = TLDresp[DNS].ns[0].rdata
        else:
            i = 0
            while len(ANS) > 15:
                ANS = TLDresp[DNS].ar[i].rdata
                i += 1

        networkLayer = IP(dst=ANS)
        transportLayer = UDP(dport=53, sport=56980)
        applicationLayer = DNS(id=random.randint(0, 10000), rd=1, qd=DNSQR(qname=siteName, qtype= 'A'))

        ANSquery = networkLayer/transportLayer/applicationLayer

        ANSresp = sr1(ANSquery, timeout=1)
        siteIP = ANSresp[DNS].an.rdata

        #voeg de domain name en overeenkomstige IP toe aan de name en IP directories.
        nameDirectory.append(siteName)
        IPDirectory.append(siteIP)

    return(siteIP)



def main():
    running = True

    #stel asynchrone sniffer in op port 53 (standaard poort voor dns querie
    t = AsyncSniffer(count=1, filter = "port 53")
    #maak een lege resulst lijst aan
    results = []
    count = 0
    hostIP = get_if_addr(conf.iface)
    #zolang de dns server runt blijf loopen
    print("starting DNS resolver")
    while(running):
        count += 1
        # start de sniffer
        t.start()
        if count == 1:
            startup()
        t.join()
        #loop daar alle gecapturde packets
        if len(results) > 0:
            print(results[0].summary())
        for packet in results:
            if packet[IP].dst == hostIP and packet[DNS].qr == 0:
                print("generating response", packet[IP].src)
                siteName = packet[DNS].qd.qname
                rd = packet[DNS].rd

                #maak een networklayer packet aan met als destination het IP address waarvan de query komt
                networkLayer = IP(dst=packet[IP].src)
                #maak een transport layer UDP packet aan met als destination port de port waarvan de query origineert en als source port port 53 (standaard voor dns queries)
                transportLayer = UDP(dport=packet[UDP].sport, sport=53)

                #vindt het overeenkomstige IP address
                siteIP = getSiteIP(siteName, rd)
                print("h")
                #bouw application layer packet
                applicationLayer = DNS(id=packet[DNS].id, #transaction id, moet zelfde zijn als id meegegeven door de client bij de reguest
                                       aa=1, #authoratative answer, geeft aan of we een authoritaire DNS server zijn
                                       qr=1, #geeft aan of het een query of response is (1 voor response)
                                       rd=packet[DNS].rd, #recursion desiseredm geeft aan of de client recursie wou
                                       qdcount=packet[DNS].qdcount, #geeft aan hoeveel questions er zijn gesteld in de packet
                                       qd=packet[DNS].qd, #de question van de client
                                       ancount=1, #geeft het aantal antwoorden in de response aan
                                       an=DNSRR(rrname=packet[DNS].qd.qname, #geeft aan voor welke domain name we antwoorden
                                                type='A', #geeft het type van de query aan (A voor een standaard host name query)
                                                ttl=1, # time to live, geeft aan hoe lang de client er mag van uitgaan dat het IP voor de host name niet verandert
                                                rdata=siteIP)) #het ip dat overeenkomt met de host name in de query

                DNSAnswer = networkLayer/transportLayer/applicationLayer
                dnsResponse = sr1(DNSAnswer, timeout=1)

                print("Domain name:", siteName, "IP:", siteIP)

        #stop de sniffer en update de results
        results = t.results



# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

