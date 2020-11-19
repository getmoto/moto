NOTE:
Whenever I'm working on this after a rebase, need to set
rds backend to rds3 in moto/backends.py

Try to leverage as much of the boto python libraries as possible. That should cut down
on cut and increase correctness

Botocore serializes requests and parses response; we need to do the opposite, so we 
can't make use of their Serializer or Parser directly, but we can use their code as
a guide for doing what we need.



Refs:
https://www.oreilly.com/library/view/designing-evolvable-web/9781449337919/ch04.html

TODO:
-serializer should be able to handle the attribute name it expects as well
 as fall back to the pythonic name