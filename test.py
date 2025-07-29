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

# def compare_texts(t1, t2):
#     import difflib
#     t1_lines = [line for line in t1.strip().splitlines()]
#     t2_lines = [line for line in t2.strip().splitlines()]
#     diff = list(difflib.ndiff(t1_lines, t2_lines))
#     result = []
#     i = 0
#     while i < len(diff):
#         line = diff[i]
#         if line.startswith("  "):
#             # Одинаковые строки
#             result.append(line[2:])
#             i += 1
#         elif line.startswith("- "):
#             # Удалено
#             if i + 1 < len(diff) and diff[i + 1].startswith("+ "):
#                 # Замена строки
#                 result.append(f"<s>{line[2:]}</s>")
#                 result.append(f"<b><i>{diff[i + 1][2:]}</i></b>")
#                 i += 2
#             else:
#                 result.append(f"<s>{line[2:]}</s>")
#                 i += 1
#         elif line.startswith("+ "):
#             # Добавлено (если не после удаления — иначе уже обработано как замена)
#             result.append(f"<b><i>{line[2:]}</i></b>")
#             i += 1
#         else:
#             i += 1
#     return "\n".join(result)




# from rasp import CheckRasp
# import asyncio


# async def test():
#     checkrasp = CheckRasp(date="02_07_2025")
#     await checkrasp.check_rasp_loop()
#     checkrasp = CheckRasp(date="21_07_2025")
#     await checkrasp.check_rasp_loop()



# asyncio.run(test())

from db import DB
from pprint import pprint
db = DB()
_ = db.get_all_usersWgroup()
for i in _.keys():
    print(i)