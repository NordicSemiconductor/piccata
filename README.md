piccata - Python CoAp Toolkit
=============================

piccata is a simple CoAP (RFC7252) toolkit compatible with Python 2.7. 

The toolkit provides basic building blocks for using CoAP in an
application. piccata handles messaging between endpoints 
(retransmission, deduplication) and request/response matching. 

Handling and matching resources, blockwise transfers, etc. is left
to the application but functions to faciliate this are provided.

piccata uses a transport abstraction to faciliate using the toolkit
for communication over different link types. Transport for a UDP 
socket is provided.

LICENSE
-------
piccata is published under the MIT license, see LICENSE for details. 

The project has been derived from [txThings](https://github.com/mwasilak/txThings)
developed by Maciej Wasilak.
