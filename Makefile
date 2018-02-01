default:
	chmod 755 dht_peer
	chmod 755 client

root :
	./dht_peer -m 1 -p 16500 -h `hostname`

peer :
	./dht_peer -m 0 -p 16501 -h `hostname` -R baseball.ccs.neu.edu -r 16500

client :
	./client -p 1234 -h `hostname` -r 16500 -R baseball.ccs.neu.edu
