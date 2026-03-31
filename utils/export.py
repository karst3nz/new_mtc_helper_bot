"""
Модуль экспорта данных в Excel
"""
import os
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from utils.db import DB
from utils.log import create_logger

logger = create_logger(__name__)


class ExcelExporter:
    def __init__(self):
        self.db = DB()
    
    async def export_hours_history(self, user_id: int, days: int = 30) -> str:
        """
        Экспорт истории пропущенных часов в Excel
        Возвращает путь к созданному файлу
        """
        logger.info(f"Экспорт истории часов для пользователя {user_id}")
        
        try:
            # Получаем данные пользователя
            user_data = await self.db.get(user_id)
            if not user_data:
                raise ValueError(f"Пользователь {user_id} не найден")
            
            # Получаем историю
            history = self.db.get_hours_history(user_id, days)
            
            # Создаем книгу Excel
            wb = Workbook()
            ws = wb.active
            ws.title = "История пропусков"
            
            # Стили
            header_font = Font(bold=True, size=12, color="FFFFFF")
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            
            border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            # Заголовок документа
            ws.merge_cells('A1:D1')
            ws['A1'] = f"История пропущенных часов - Пользователь {user_data[2] or user_id}"
            ws['A1'].font = Font(bold=True, size=14)
            ws['A1'].alignment = Alignment(horizontal="center")
            
            # Информация о пользователе
            ws['A2'] = "Группа:"
            ws['B2'] = user_data[3]
            ws['A3'] = "Текущие пропуски:"
            ws['B3'] = user_data[5]
            ws['A4'] = "Период:"
            ws['B4'] = f"Последние {days} дней"
            
            # Заголовки таблицы
            headers = ['№', 'Дата', 'Пропущено часов', 'День недели']
            ws.append([])  # Пустая строка
            header_row = 6
            
            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=header_row, column=col_num)
                cell.value = header
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = border
            
            # Данные
            if history:
                weekdays = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
                
                for idx, row in enumerate(history, 1):
                    date_str = row[0]
                    hours = row[1]
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    weekday = weekdays[date_obj.weekday()]
                    
                    data_row = [idx, date_obj.strftime("%d.%m.%Y"), hours, weekday]
                    ws.append(data_row)
                    
                    # Применяем границы
                    for col_num in range(1, len(headers) + 1):
                        ws.cell(row=header_row + idx, column=col_num).border = border
                        ws.cell(row=header_row + idx, column=col_num).alignment = Alignment(horizontal="center")
                
                # Итоговая строка
                total_row = header_row + len(history) + 1
                ws.cell(row=total_row, column=1).value = "ИТОГО:"
                ws.cell(row=total_row, column=1).font = Font(bold=True)
                ws.cell(row=total_row, column=3).value = sum([row[1] for row in history])
                ws.cell(row=total_row, column=3).font = Font(bold=True)
                
                for col_num in range(1, len(headers) + 1):
                    ws.cell(row=total_row, column=col_num).border = border
            else:
                ws.append(['', 'Нет данных за указанный период', '', ''])
            
            # Автоширина колонок
            for col in range(1, len(headers) + 1):
                max_length = 0
                column = get_column_letter(col)
                for cell in ws[column]:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2) * 1.2
                ws.column_dimensions[column].width = adjusted_width
            
            # Сохранение файла
            filename = f"hours_history_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join("data", filename)
            
            # Создаем директорию если не существует
            os.makedirs("data", exist_ok=True)
            
            wb.save(filepath)
            logger.info(f"Файл успешно создан: {filepath}")
            
            return filepath
        
        except Exception as e:
            logger.error(f"Ошибка экспорта для пользователя {user_id}: {e}")
            raise
    
    async def export_schedule_changes(self, group_id: str = None, limit: int = 50) -> str:
        """
        Экспорт истории изменений расписания в Excel
        """
        logger.info(f"Экспорт истории изменений расписания для группы {group_id or 'все'}")
        
        try:
            # Получаем историю изменений
            changes = self.db.get_schedule_changes(group_id, limit)
            
            # Создаем книгу Excel
            wb = Workbook()
            ws = wb.active
            ws.title = "История изменений"
            
            # Стили
            header_font = Font(bold=True, size=12, color="FFFFFF")
            header_fill = PatternFill(start_color="E74C3C", end_color="E74C3C", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            
            border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            # Заголовок
            ws.merge_cells('A1:E1')
            ws['A1'] = f"История изменений расписания" + (f" - Группа {group_id}" if group_id else "")
            ws['A1'].font = Font(bold=True, size=14)
            ws['A1'].alignment = Alignment(horizontal="center")
            
            # Заголовки таблицы
            headers = ['№', 'Дата расписания', 'Группа', 'Изменения', 'Время записи']
            ws.append([])
            header_row = 3
            
            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=header_row, column=col_num)
                cell.value = header
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = border
            
            # Данные
            if changes:
                for idx, row in enumerate(changes, 1):
                    date_str = row[0]
                    group = row[1]
                    diff_text = row[2][:100] + "..." if len(row[2]) > 100 else row[2]  # Обрезаем длинный текст
                    created_at = row[3]
                    
                    data_row = [idx, date_str, group, diff_text, created_at]
                    ws.append(data_row)
                    
                    # Применяем границы
                    for col_num in range(1, len(headers) + 1):
                        ws.cell(row=header_row + idx, column=col_num).border = border
                        if col_num != 4:  # Не центрируем текст изменений
                            ws.cell(row=header_row + idx, column=col_num).alignment = Alignment(horizontal="center")
            else:
                ws.append(['', '', 'Нет данных', '', ''])
            
            # Автоширина колонок
            ws.column_dimensions['A'].width = 5
            ws.column_dimensions['B'].width = 15
            ws.column_dimensions['C'].width = 10
            ws.column_dimensions['D'].width = 50
            ws.column_dimensions['E'].width = 20
            
            # Сохранение файла
            filename = f"schedule_changes_{group_id or 'all'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join("data", filename)
            
            os.makedirs("data", exist_ok=True)
            wb.save(filepath)
            logger.info(f"Файл успешно создан: {filepath}")
            
            return filepath
        
        except Exception as e:
            logger.error(f"Ошибка экспорта истории изменений: {e}")
            raise


# Глобальный экземпляр
excel_exporter = ExcelExporter()
