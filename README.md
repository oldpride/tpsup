# tpsup
Tradeplant Support 


Microservices design

Source code has been modularized, so should be the deployed app.

Monolithic app: smashed modules into one software.

Microservices architecture trade-off
+ New developer only need to focus on one service.
+ Highly scalable
+ Domain Driven Design (DDD): each developer is  specialized
+ Communicate with REST API, so that each component can be implemented using different languages
+ Frequent release, parallel release
+ Security per service

- require discovery service
- delay by remote call
- difficult integration: difficult to move code between services
- difficult troubleshooting: decentralized structure
- transaction security
- require infrastructure automation

REST/RESTful: Representational State Transfer

Spring Boot: on top of Spring framework，all ingredients are ready, only need customization

