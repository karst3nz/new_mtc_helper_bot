# # class Test:
# #     def __init__(self) -> None:
# #         pass

# #     def test2(self):
# #         return "2"

# #     @property
# #     def test1(self):
# #         return self

# # _test = Test()
# # print(_test.test1.test2())


# text1 = """
# 1 | test | 000 | test_teach
# 2 | test | 000 | test_teach
# 3 | test | 010 | test_teach
# """

# text2 = """
# 1 | test | 000 | test_teach
# 2 | test | 000 | test_teach
# 3 | test11 | 020 | test_teach
# """






# from rasp import CheckRasp
# import asyncio


# async def test():
#     checkrasp = CheckRasp(date="02_07_2025")
#     await checkrasp.check_rasp_loop()
#     checkrasp = CheckRasp(date="21_07_2025")
#     await checkrasp.check_rasp_loop()



# asyncio.run(test())


# from pprint import pp


# groups = ['1111', '1191', '1195', '1196', '1291', '1391', '1392', '1395', '1491', '1495', '1595', 
# '2111', '2191', '2195', '2196', '2211', '2291', '2311', '2391', '2392', '2395', '2491', '2495', '2595', '2596', 
# '3111', '3191', '3195', '3196', '3311', '3312', '3391', '3392', '3393', '3395', '3491', '3495', '3595', '3596', 
# '4111', '4191', '4192', '4193', '4311', '4312', '4391', '4392', '4393', '4394', '4491', '4595', '4596']


# groups.sort()
# print(groups)


# from db import DB


# db = DB()
# db.return_user_dataclass("1823563959")

import asyncio



async def get_all_promo_stats(): print(1)



async def _():
    asyncio.create_task(get_all_promo_stats())


asyncio.run(_())