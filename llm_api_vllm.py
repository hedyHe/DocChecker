# -*- coding: utf-8 -*-

"""
调用各个大模型的接口

"""
import os
# os.environ['CUDA_VISIBLE_DEVICES'] = '0,1,2,3'

import random
import json
import traceback
import time

from copy import deepcopy
import optparse
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams

class Qwen(object):
	"""docstring for Qwen"""
	def __init__(self, model='qwen2.5_32b', temperature=None):
		print('当前模型:', model)
		if 'ds_qwen2.5_14b' in model:
			model_name = "/data2/models/DeepSeek-R1-Distill-Qwen-14B"
		elif 'qwen2.5_32b' in model:
			model_name = "/data2/Qwen/Qwen2.5-32B-Instruct"
			if not os.path.exists(model_name):
				model_name = "/root/autodl-tmp/data/Qwen2.5-32B-Instruct"
			if not os.path.exists(model_name):
				model_name = "/data2/models/Qwen2.5-32B-Instruct"
		elif 'qwen2.5_7b_lora' in  model:
			model_name = "/data1/hy/output/qwen25_7b_lora_sft"
			model_name = "/data1/hy/output/qwen25_7b_lora_sft_1"
		elif 'qwen2.5_7b' in model:
			model_name = "/data2/Qwen/Qwen2.5-7B-Instruct"
			if not os.path.exists(model_name):
				model_name = "/data2/models/Qwen2.5-7B-Instruct"
		elif 'qwen2.5_14b_lora_1_3_new' in model:
			model_name = '/data2/hy/LLaMA-Factory-main/output/qwen25_14b_lora_sft_1_3_new'
		elif 'qwen2.5_14b_lora_1_3_filter' in model:
			model_name = '/data2/hy/LLaMA-Factory-main/output/qwen25_14b_lora_sft_1_3_filter'
		elif 'qwen2.5_14b_lora_1_5' in model:
			model_name = '/data2/hy/LLaMA-Factory-main/output/qwen25_14b_lora_sft_1_5' 
		elif 'qwen2.5_14b_lora_1_3' in model:
			model_name = '/data2/hy/1_LLaMA-Factory-main/output/qwen25_14b_lora_sft_1_3' 
		elif 'qwen2.5_14b_lora' in model:
			model_name = '/data1/hy/output/qwen25_14b_lora_sft' 
			if not os.path.exists(model_name):
				model_name = '/data2/hy/LLaMA-Factory-main/output/qwen25_14b_lora_sft' 
		elif 'qwen2.5_14b' in model:
			model_name = "/data2/Qwen/Qwen2.5-14B-Instruct"
			if not os.path.exists(model_name):
				model_name = "/root/autodl-tmp/data/Qwen2.5-14B-Instruct"
			if not os.path.exists(model_name):
				model_name = "/data2/models/Qwen2.5-14B-Instruct"
		elif 'qwen2.5_72b' in model:
			model_name = "/data2/models/Qwen2.5-72B-Instruct"
			if not os.path.exists(model_name):
				model_name = "/data2/Qwen/Qwen2.5-72B-Instruct"
		# elif 'qwen_14b' in model:
		# 	model_name = "/data/drc/Qwen-14B"
		elif 'fin_qwen_14b' in model:
			model_name = "/home/dell/models/Tongyi-Finance-14B-Chat"
		else:
			print('未考虑到的模型', model)
			exit()
		print('model_name:', model_name)

		self.tokenizer = AutoTokenizer.from_pretrained(model_name)
		
		# self.sampling_params_0 = SamplingParams(temperature=0.9, repetition_penalty=1.05, max_tokens=500)   #max_token是指新生成的token数
		# # self.sampling_params = SamplingParams(temperature=self.temperature, repetition_penalty=1.05, max_tokens=512)
		# self.vllm = LLM(model = model_name, gpu_memory_utilization=0.7, max_model_len=20000)


		if "72b" in model:
			self.sampling_params_0 = SamplingParams(temperature=0.9, repetition_penalty=1.05, max_tokens=2000, n=2)   #max_token是指新生成的token数,n是生成几个答案
			self.vllm = LLM(model = model_name, tensor_parallel_size=2, max_model_len=8000, gpu_memory_utilization=0.9) #分布在n个gpu上
		else:
			self.sampling_params_0 = SamplingParams(temperature=0.9, repetition_penalty=1.05, max_tokens=2000, n=2)   #max_token是指新生成的token数,n是生成几个答案
			# self.vllm = LLM(model = model_name, dtype='half', tensor_parallel_size=4, max_model_len=8000, gpu_memory_utilization=0.98) #分布在n个gpu上

			self.vllm = LLM(model = model_name, max_model_len=23000, gpu_memory_utilization=0.9) 

	def get_response(self, queries):
		prompts = []
		for x in queries:
			messages = [
			    {"role": "system", "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."},
			    {"role": "user", "content": x}
			]

			text = self.tokenizer.apply_chat_template(
			    messages,
			    tokenize=False,
			    add_generation_prompt=True
			)
			prompts.append(text)
			
		all_res = []

		outputs = self.vllm.generate(prompts, self.sampling_params_0)
		for output in outputs:
			prompt = output.prompt
			generate_text = output.outputs[0].text   #只取第一个答案

			all_res.append([prompt, generate_text])

		return all_res

	def get_multi_response(self, queries):
		#一个答案获取多个结果
		prompts = []
		for x in queries:
			messages = [
			    {"role": "system", "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."},
			    {"role": "user", "content": x}
			]

			text = self.tokenizer.apply_chat_template(
			    messages,
			    tokenize=False,
			    add_generation_prompt=True
			)
			prompts.append(text)
			
		all_res = []

		outputs = self.vllm.generate(prompts, self.sampling_params_0)
		for i, v in enumerate(outputs):
			all_res.append([queries[i], []])
			for output in v.outputs:
				generate_text = output.text
				all_res[-1][1].append(generate_text)

		return all_res


if __name__ == '__main__':
	# llm = Qwen('qwen2.5_7b')
	# llm = Qwen('deepseek-r1-qwen2.5_7b')
	# llm = Qwen('qwen2.5_32b', 0.9)
	llm = Qwen('qwen2.5-72b')
	start_time = time.time()
	res = llm.get_response(['角色：你是一个CN-DBpedia知识库数据治理专家，需判断某个属性下的两个属性值的语义是否相同，以便后续数据的规范化。\n输入格式：\n属性名：[属性名称，如性别、国籍等]\n值1：[第一个属性值，如女性]\n值2：[第二个属性值，如female]\n分析步骤：\n1.格式、语言处理：\n-排除大小写、缩写、全称的影响。\n-处理特殊符号（如“&”和“and”等价）。\n-若涉及多语言（中英文），可先将英文翻译成中文。\n-抓重点，忽略值中不相关的信息，如“性别”下的值“男足球”中“男”是重点，“足球”不相关。\n2.定义解析：\n-分别解释值1和值2在知识库中的标准定义。\n3.来源验证：\n检查值1和值2在知识库中是否被明确标注为同义词、别名或上下文关系。\n4.最终判断：\n-根据以上分析，给出“相同”或“不同”的结论。\n输出格式：\n-结论：[相同/不同/不确定]\n输入：\n属性名：小说状态\n值1：未能完成的断更小说\n值2：断更\n-结论：'])
	print(res)
	end_time = time.time()
	print('time:', int(end_time-start_time))
	# exit()
	for i in range(1):
		res = llm.get_response(['Give me a short introduction to large language model.'])
		print('------------\n', res)
	end_time = time.time()
	print('time:', int(end_time-start_time))	

	# print(time.time())
	# prompt = '角色：你是一个CN-DBpedia知识库数据治理专家，需判断某个属性下的两个属性值的语义是否相同，以便后续数据的规范化。\n输入格式：\n属性名：[属性名称，如性别、国籍等]\n值1：[第一个属性值，如女性]\n值2：[第二个属性值，如female]\n分析步骤：\n1.格式、语言处理：\n-排除大小写、缩写、全称的影响。\n-处理特殊符号（如“&”和“and”等价）。\n-若涉及多语言（中英文），可先将英文翻译成中文。\n-抓重点，忽略值中不相关的信息，如“性别”下的值“男足球”中“男”是重点，“足球”不相关。\n2.定义解析：\n-分别解释值1和值2在知识库中的标准定义。\n3.来源验证：\n检查值1和值2在知识库中是否被明确标注为同义词、别名或上下文关系。\n4.最终判断：\n-根据以上分析，给出“相同”或“不同”的结论。\n输出格式：\n-结论：[相同/不同/不确定]\n输入：\n属性名：小说状态\n值1：未能完成的断更小说\n值2：断更\n-结论：'
	# prompts = [prompt, '请你自我介绍下']
	# res = get_response(prompts)
	# print(res)
	# print(time.time())
	# res = get_response(prompts, 0.9)
	# print(res)
	# print(time.time())