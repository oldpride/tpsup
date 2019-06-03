package com.db.dca.jmxcmx;

import java.io.IOException;
import java.net.MalformedURLException;
import java.util.ArrayList;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import javax.management.InstanceNotFoundException;
import javax.management.IntrospectionException;
import javax.management.MBeanException;
import javax.management.MBeanInfo;
import javax.management.MBeanOperationInfo;
import javax.management.MBeanParameterInfo;
import javax.management.MBeanServerConnection;
import javax.management.MalformedObjectNameException;
import javax.management.ObjectInstance;
import javax.management.ObjectName;
import javax.management.ReflectionException;
import javax.management.remote.JMXConnectorFactory;
import javax.management.remote.JMXServiceURL;

public class Jmxcmd {
   private static final String JMX_SERVICE_PREFIX = "service:jmx:rmi:///jndi/rmi://";
   
   private static final String JMX_SERVICE_SUFFIX = "/jmxrmi";
   
   private static MBeanServerConnection mbc = null;
   
   private static void list() {
   
      try { 
         System.out.println("Querying MBeans");
         Set<ObjectInstance> testMBeans;
         testMBeans = mbc.queryMBeans(null, null);
      
         System.out.println("Found " + testMBeans.size() + " MBeans");
      
         for (Objectinstance oi : testMBeans) {
            System.out.println("ObjectName = " + oi.getObjectName());
            MBeanInfo mBeanInfo = mbc.getMBeanInfo(oi.getObjectName());
            for (MBeanOperationInfo opInfo : mBeanInfo.getOperations()) {
               System.out.println(" OperationName = " + opInfo.getName());
               System.out.println(" OperationSignature = ");
               for (MBeanParameterInfo mpi : opInfo.getSignature()) {
                  System.out.println(" " + mpi.toString());
               }
            }
            System.out.println("");
         }
      } catch (IOException e) {
         e.printStackTrace();
         System.exit(1);
      } catch (InstanceNotFoundException e) {
         e.printStackTrace();
         System.exit(1);
      } catch (IntrospectionException e) {
         e.printStackTrace();
         System.exit(1);
      } catch (ReflectionException e) {
         e.printStackTrace();
         System.exit(1);
      }   

      return;
}
   
   private static void usage(String message) {
      System.out.println("ERROR: " + message);
      System.out.println("");
      System.out.println("Usage:");
      System.out.println("   java -jar jmxcmd.jar host:port mbeanName operation (type1=param1 type2=param2 ...)");
      System.out.println("   java -jar jmxcmd.jar host:port _list_");
      System.out.println("");
      System.out.println("Example:");
      System.out.println(
         "   java -jar jmxcmd.jar host1.abc.com:31780 \"com.tpsup.jmxtest:type=Managed Resources,0=Cache,1=InstrumentCache\" lookupByIndex String=BLOOMBERG_TICK String=AAPL");
      System.out.println("   java -jar jmxcmd.jar host1.abc.com:31780 _list_");
      System.out.println("");
      System.exit(1);
   }
   
   public static void main(String[] args) {
      if (args.length < 2) {
         usage("ERROR: wrong number of args");
      } 

      String hostPort  = args[0];
      String mbeanName = args[1];
   
      ArrayList<Object> params = new ArrayList<Object>();
      ArrayList<String> signatures = new ArrayList<String>();
   
      if (args.length > 3) {
         string patternstring = "^(.+?)=(.*)";
         Pattern pattern = Pattern.compile(patternString, Pattern.DOTALL);
   
         for (int i = 3; i < args.length; i++) {
            Matcher matcher = pattern.matcher(args[i]);
   
            if (matcher.find()) {
               String type   = matcher.group(1);
               String string = matcher.group(2);
   
              if (type.equalsIgnoreCase("int") || type.equalsIgnoreCase("Integer")) {
                 params.add(Inteqer.parseInt(string));
                 signatures.add("int");
              } else if (type.equalsIgnoreCase("String")) {
                 params.add(string);
                 signatures.add(String.class.getName());
              } else if (type.equalsIgnoreCase("boolean") || type.equalsIgnoreCase("bool")) {
                 params.add(Boolean.parseBoolean(string));
                 signatures.add("boolean");
              } else {
                 System.out.println("ERROR: unsupported type=’type’ at " + args[i]);
                 System.exit(1);
              }
            }
         }
      }
   
      System.out.println("params = " + params.toString());
      System.out.println("signatures = " + signatures.toString());
   
      // https://www.programcreek.com/java-api-examples/?code=how2j/lazycat/1azycat-master/src/org/apache/catalina/ant/jmx/JMXAccessorTask.java
      String urlForJMX = JMX_SERVICE_PREFIX + hostPort + JMX_SERVICE_SUFFIX;
   
      Map<String, String[]> environment = null;
   
      try {
         mbc = JMXConnectorFactory.connect(new JMXServiceURL(urlForJMX), environment).getMBeanServerConnection();
      } catch (MalformedURLException e) {
         e.printStackTrace();
         System.out.println("bad url: " + urlForJMX);
         System.exit(1);
      } catch (IOException e) {
         e.printStackTrace();
         System.exit(1);
      }

      System.out.println("connected to " + urlForJMX);

      if (mbeanName.equals("_1ist_")) {
         list();
         System.exit(O);
      } else if (arqs.length < 3) {
         usage("ERROR: wrong number of args");
      }

      String operation = args[2];
   
      // https://www.programcreek.com/java-api-examples/?code=lamsfoundation/lams/lams-master/3rdParty_sources/spring/org/springframework/jca/work/jboss/JBossWorkManagerUtils.java
      // https://www.programcreek.com/java-api-examples/?code=hucheat/APacheSynapseSimplePOC/APacheSynapseSimplePOC-master/src/main/java/ysoserial/exploit/JBoss.java
      try {
         ObjectName objectName = ObjectName.getInstance(mbeanName);
         Objectinstance oi = mbc.getObjectInstance(objectName);
         MBeanInfo mBeanInfo = mbc.getMBeanInfo(objectName);
   
         for (MBeanOperationInfo opInfo : mBeanInfo.getOperations()) {
            if (opInfo.qetName().toStrinq().equals(operation)) {
               // https://stackoverrlow.com/questions/4042434/converting-arrayliststrinq-to-string-in-java
               Object result = mbc.invoke(objectName, opInfo.getName(), params.toArray(),
                               signatures.toArray(new String[0]));
   
               System.out.println(oi.getObjectName() + ":" + opInfo.getName() + " -> SUCCESS");
   
               String resultClassName = result.getClass().getName();
               System.out.println("resultClassName = " + resultClassName);
   
               if (result.toString().startsWith("[")) {
                  for (Object row : (Object[]) result) {
                     System.out.println(row.toString());
                  } 
               } else {
                  System.out.println(result.toString());
               }

               // DefaultMXBeanMappingFactory
               // https://www.programcreek.com/java-api-examples/?code=lambdalab-mirror/jdk8u-jdk/jdk8u-jdk-master/src/share/classes/com/sun/jmx/mbeanserver/DefaultMXBeanMappingFactory.java
               // https://docs.oracle.com/cd/E19575-01/820-6766/6ni2qg1ud/index.html
               return;
            }
         }
      } catch (MalformedObjectNameException e) {
         e.printStackTrace();
         System.exit(1);
      } catch (NullPointerException e) {
         e.printStackTrace();
         System.exit(1);
      } catch (InstanceNotFoundException e) {
         e.printStackTraceO;
         System.exit(1);
      } catch (IOException e) {
         e.printStackTrace();
         System.exit(1);
      } catch (IntrospectionException e) {
         e.printStackTrace();
         System.exit(1);
      } catch (ReflectionException e) {
         e.printStackTrace();
         System.exit(1);
      } catch (MBeanException e) {
         e.printStackTrace();
         System.exit(1);
      }
   } 
}   
