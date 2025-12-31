import json
with open("json/example1.json",'r',encoding='utf-8') as f:
   data_json=f.read()
room={"4f75ca59-06b8-4323-95e3-3c2100d454d1":"阳台外围墙体1","e894824b-54a5-4b40-8fff-a62dcbfad81e":"阳台/主卧/主卧卫生间外围墙体1",
      "179acb4e-4ad5-466f-972a-2744b47eec64":"儿童房/次卧2外围墙体1","201672ff-79ea-461c-b639-171e96df02f7":"次卧2外围墙体1",
      "99953e21-07fb-4fc3-9dbb-09835f4f57e8":"次卧/书房外围墙体1",'197da975-89e9-400e-ba05-edf547658c1d':"主卧卫生间外围墙体1",
      "6b3e33ee-040c-48f8-81c9-db8f5eed771c":'次卧1/次卧2外围墙体1',"49d6efa3-6c5d-4f55-9212-4c3540c4a380":"书房外围墙体1",
      "99118896-53dd-4718-b56d-70ebd80ec615":"书房外围墙体2","ea660a4a-7e6f-4613-8f40-494b7bb89eba":"客餐厅外围墙体1",
      "b00c5f8e-b32e-4fbf-8672-2f4433c3ec51":"客厅卫生间外围墙体1",'4edf9a89-30df-479c-bbc2-870e23155794':"客厅卫生间/厨房外围墙体1",
      "287948c5-51dc-4f30-b05d-5ef2bcc2de66":"厨房外围墙体1",'c4e8f4ae-dfd1-4a06-b6d8-2ee3068a86e0':"阳台外围墙体2"}
for id,value in room.items():
   data_json=data_json.replace(id,value)
with open('json/example1.json','w',encoding='utf-8') as f:
   f.write(data_json)