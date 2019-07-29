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

AWS

Public cloud: share with others
Private cloud: isolated on vendor side, or buy own cloud hardware and hire own team
Hybrid: mix on-premise, private, public cloud
 

Infrastructure as service: provide OS

Platform as service: provide dashboard: Tomcat, PHP, Apache

Software as service: provide software, eg, Google docs

Service domains:
Compute, Storage, database, security,
Management, Customer Engagement, app integration

Compute: 
EC2 - elastic compute cloud, IAS
elastic beanstalk - advanced EC2, with suite of software, PAS, eg, web server
Aws lambda - automated ec2, auto scale
Elastic Load balancing
Aws auto scaling
Elastic container registry - like docker
Elastic container service






