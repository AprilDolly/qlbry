#!/usr/bin/python3
#making Claim a sublcass of dict this time, so it isn't as shitty
import requests
import subprocess
from subprocess import DEVNULL,PIPE
import json
from json.decoder import JSONDecodeError
import random

class Account:
	def __init__(self,dic,lbry):
		print(dic)
		print(dic.keys())
		self.__dict__.update(dic)
		self.lbry=lbry

class DictWrapper:
	def __init__(self,d):
		self.update(d)

class Claim(dict):
	#may just turn into a dict
	"""
	PARAMETERS:
	#USEFUL:
	address: idk
	amount: amount staked in the claim by the creator
	canonical_url: the url of the claim
	claim_id: idk lel
	name: the name of the video or channel or whatever
	
	"""
	def __init__(self,claim_id,name,lbry,dic={}):
		super().__init__()
		self.update(dic)
		if not "name" in self.keys():
			self["name"]=name
		self.get_channel()
		self.lbry=lbry
		self.id=claim_id
		self.name=name
		self._resolved=False
	def __getattr__(self,attr):
		#treats key, value as attribute
		try:
			return self[attr]
		except KeyError:
			if True:
				return ""
			else:
				try:
					self.resolve()
					return self[attr]
				except KeyError:
					self.get()
					return self[attr]
	def channel_claims(self):
		target=None
		if "signing_channel" in self.keys():
			target=self["signing_channel"]["name"]
		elif self["value_type"]=="channel":
			target=self
		if target!=None:
			for c in self.lbry.get_channel_claims(target):
				yield c
		else:
			yield None
	def get_channel(self):
		if "signing_channel" in self.keys():
			if type(self["signing_channel"])==dict:
				try:
					sc_dict=self["signing_channel"]
					self["signing_channel"]=Claim(sc_dict["claim_id"],sc_dict["name"],self.lbry,dic=sc_dict)
				except KeyError:
					pass
	def resolve(self):
		if self._resolved:
			return
		if self.id in self.lbry.resolved_claims.keys():
			self.update(self.lbry.resolved_claim_data[self["name"]])
		else:
			print("resolving",self.name,self.id)
			try:
				newdata=self.lbry.resolved_claim_data[self.name]
			except KeyError:
				self.update(self.lbry.resolve(self["name"]))
		self.get_channel()

	def get(self):
		self.update(self.lbry.get(self))
	def get_comments(self,offset):
		pass
		#https://comments.odysee.com/api/v2?m=comment.List
	def to_dict(self):
		dic={}
		for k in self.keys():
			dic[k]=self[k]
		return dic
			
				
		
		
class LBRY:
	def __init__(self,lbrynet_name="lbrynet",*args,**kwargs):
		self.lbrynet_name=lbrynet_name
		self.lbrynet_exists=self.test_lbrynet()
		self.resolved_claim_data={}
		self.resolved_claims={}
	def test_lbrynet(self):
		try:
			cmd_process=subprocess.Popen([self.lbrynet_name,"status"],stdout=PIPE,stderr=PIPE)
			out=cmd_process.stdout.read().decode('utf-8')
			if "Could not connect to daemon. Are you sure it's running?" in out:
				return False
			else:
				return True
		except FileNotFoundError:
			return False
	def start(self):
		self.lbrynet_process=subprocess.Popen([self.lbrynet_name,'start'],stdout=PIPE,stderr=PIPE)
		while True:
			line=self.lbrynet_process.stderr.readline().decode('utf-8')
			print(line)
			if 'Done setting up file manager' in line:
				return
			elif "finished shutting down" in line:
				return
	def stop(self):
		self.lbrynet_command('stop')
		
		
	def get_channel_claims(self,channel):
		if type(channel)==str:
			channel={"name":channel}
		rsp=self.lbrynet_command("claim","search","--channel={}".format(channel["name"]),"--order_by=release_time")
		#print(rsp)
		for j in rsp["items"]:
			yield Claim(j["claim_id"],j["name"],self,dic=j)
		total_pages=rsp["total_pages"]
		if total_pages>1:
			for i in range(2,total_pages+1):
				rsp2=self.lbrynet_command("claim","search","--channel={}".format(channel["name"]),"--page={}".format(i),"--order_by=release_time")
				for j in rsp2["items"]:
					yield Claim(j["claim_id"],j["name"],self,dic=j)
		
		
	def get(self,claim):
		if self.lbrynet_exists:
			return self.lbrynet_command("get",claim["name"])
		else:
			purl="https://api.na-backend.odysee.com/api/v1/proxy?m=get"
			uri="lbry://{}".format(claim["name"])
			pdata={"id":random.randrange(10,100000),"jsonrpc":"2.0","method":"get","params":{"uri":uri,"save_file":"false"}}
			rsp=requests.post(purl,data=json.dumps(pdata))
			
			try:
				return rsp.json()["result"]
			except:
				print(print(rsp.json()))
	def lbrynet_command(self,*args,args_list=[]):
		args=[self.lbrynet_name]+list(args)+args_list
		cmd_process=subprocess.Popen(args,stdout=PIPE,stderr=PIPE)
		out=cmd_process.stdout.read().decode('utf-8')
		try:
			return json.loads(out)
		except JSONDecodeError:
			return out
		
	def get_accounts(self):
		accounts=[]
		accounts_json=self.lbrynet_command('account','list')
		for acc in accounts_json['items']:
			accounts.append(Account(acc,self))
	def resolve(self,claim_name):
		if self.lbrynet_exists:
			return self.lbrynet_command("resolve",claim_name)
		else:
			purl="https://api.na-backend.odysee.com/api/v1/proxy?m=resolve"
			pdata={"jsonrpc":"2.0","method":"resolve","params":{"urls":["lbry://{}".format(claim_name)],"include_is_my_output":True,"include_purchase_receipt":True}}
			return requests.post(purl,data=json.dumps(pdata)).json()["result"]
	def resolve_batch(self,claims):
		if self.lbrynet_exists:
			names=[]
			for c in claims:
				#print(c)
				names.append(c["name"])
			
			resolved=self.lbrynet_command("resolve",args_list=names)
			try:
				for k in resolved.keys():
					for c in claims:
						if c["name"] in k:
							self.resolved_claim_data[c["name"]]=resolved[k]
							break
			except AttributeError:
				pass
			#print(self.resolved_claim_data)
		else:
			claim_urls=[]
			for c in claims:
				claim_urls.append("lbry://{}".format(c.name))
			purl="https://api.na-backend.odysee.com/api/v1/proxy?m=resolve"
			pdata={"jsonrpc":"2.0","method":"resolve","params":{"urls":claim_urls,"include_is_my_output":True,"include_purchase_receipt":True}}
			resolved= requests.post(purl,data=json.dumps(pdata)).json()["result"]
			self.resolved_claim_data.update(resolved)
		results_resolved=[]
		for k in self.resolved_claim_data.keys():
			for c in claims:
				if c["name"] in k:
					results_resolved.append(Claim("","",self,dic=self.resolved_claim_data[k]))
					break
		return results_resolved
	def search_continuously(self,query,mode="odysee",size=20):
		for r in self.search(query,mode=mode,size=size,offset=0):
			yield r
		i_offset=1
		while True:
			#do stuff
			results=self.search(query,mode=mode,size=size,offset=i_offset*size)
			#print(len(results))
			if len(results)==0:
				break
			elif type(results)==str:
				print("RESULTS ARE str:",results)
			else:
				for r in results:
					yield r
			i_offset+=1
		
	
	def search(self,query,mode='odysee',size=20,offset=0,nsfw=False,resolve_results=True,**kwargs):
		#print("searching for:{}".format(query))
		if mode=='lbry' and self.lbrynet_exists:
			r_json=self.lbrynet_command('claim','search',query)
			results=[]
			for item in r_json['items']:
				results.append(Claim("","",self,dic=item))
			return results
		elif mode=='odysee' or self.lbrynet_exists==False:
			results=[]
			if nsfw or nsfw=="true":
				nsfw='true'
			else:
				nsfw='false'
			r=requests.get('https://lighthouse.odysee.com/search?s={}&size={}&from={}&nsfw={}'.format(query,size,offset,nsfw))
			print(len(r.json()))
			results=[]
			for j in json.loads(r.text):
				#print(r.text)
				results.append(Claim(j["claimId"],j["name"],self))
			if resolve_results:
				return self.resolve_batch(results)
			return results
	def __getattr__(self,attr):
		if attr=='cmd':
			return self.lbrynet_command
			
if __name__=='__main__':
	lbry=LBRY(lbrynet_name="lbrynet")
	lbry.test_lbrynet()
	for r in lbry.search_continuously("reallygraceful"):
		pass#print(r["name"])
		
	
