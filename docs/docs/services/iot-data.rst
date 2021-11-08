.. _implementedservice_iot-data:

========
iot-data
========



- [X] delete_thing_shadow
  after deleting, get_thing_shadow will raise ResourceNotFound.
        But version of the shadow keep increasing...
        

- [ ] get_retained_message
- [X] get_thing_shadow
- [ ] list_named_shadows_for_thing
- [ ] list_retained_messages
- [X] publish
- [X] update_thing_shadow
  
        spec of payload:
          - need node `state`
          - state node must be an Object
          - State contains an invalid node: 'foo'
        


