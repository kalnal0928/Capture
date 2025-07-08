import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import pyautogui
from datetime import datetime
import os
import threading

# 모니터 정보를 위한 import
try:
    import screeninfo
    SCREENINFO_AVAILABLE = True
except ImportError:
    SCREENINFO_AVAILABLE = False
    print("screeninfo 패키지가 없습니다. pip install screeninfo로 설치하면 개별 모니터 캡쳐가 가능합니다.")

# Windows API 사용을 위한 import
try:
    import win32gui
    import win32api
    import win32con
    import win32ui
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("pywin32 패키지가 없습니다. pip install pywin32로 설치하면 더 정확한 모니터 감지가 가능합니다.")

class RegionSelector:
    def __init__(self, parent_root, callback):
        self.parent_root = parent_root
        self.callback = callback
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.selection_window = None
        self.canvas = None
        
    def start_selection(self):
        """영역 선택 시작"""
        try:
            # 전체 화면 크기의 반투명한 창 생성
            self.selection_window = tk.Toplevel(self.parent_root)
            self.selection_window.attributes('-fullscreen', True)
            self.selection_window.attributes('-alpha', 0.3)
            self.selection_window.attributes('-topmost', True)
            self.selection_window.configure(bg='gray')
            self.selection_window.overrideredirect(True)
            
            # 화면 크기 가져오기
            screen_width = self.selection_window.winfo_screenwidth()
            screen_height = self.selection_window.winfo_screenheight()
            
            # 캔버스 생성
            self.canvas = tk.Canvas(self.selection_window, 
                                   width=screen_width,
                                   height=screen_height,
                                   highlightthickness=0,
                                   bg='gray')
            self.canvas.pack(fill='both', expand=True)
            
            # 마우스 이벤트 바인딩
            self.canvas.bind('<Button-1>', self.on_click)
            self.canvas.bind('<B1-Motion>', self.on_drag)
            self.canvas.bind('<ButtonRelease-1>', self.on_release)
            
            # 키보드 이벤트 바인딩 (ESC로 취소)
            self.selection_window.bind('<Escape>', self.cancel_selection)
            self.selection_window.bind('<KeyPress>', self.on_key_press)
            self.selection_window.focus_set()
            
            # 안내 텍스트
            self.canvas.create_text(
                screen_width // 2, 50,
                text="마우스로 드래그하여 영역을 선택하세요 (ESC: 취소)",
                fill='white', font=('Arial', 16, 'bold')
            )
            
        except Exception as e:
            print(f"영역 선택 초기화 오류: {e}")
            self.callback(None)
    
    def on_click(self, event):
        """마우스 클릭 시작"""
        self.start_x = event.x
        self.start_y = event.y
        
        # 기존 사각형 제거
        if self.rect_id:
            self.canvas.delete(self.rect_id)
    
    def on_drag(self, event):
        """마우스 드래그 중"""
        if self.start_x is not None and self.start_y is not None:
            # 기존 사각형 제거
            if self.rect_id:
                self.canvas.delete(self.rect_id)
            
            # 새 사각형 그리기
            self.rect_id = self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline='red', width=3, fill='red', stipple='gray50'
            )
    
    def on_release(self, event):
        """마우스 버튼 릴리즈"""
        if self.start_x is not None and self.start_y is not None:
            # 선택 영역 계산
            x1 = min(self.start_x, event.x)
            y1 = min(self.start_y, event.y)
            x2 = max(self.start_x, event.x)
            y2 = max(self.start_y, event.y)
            
            # 최소 크기 체크
            if abs(x2 - x1) > 10 and abs(y2 - y1) > 10:
                self.selection_window.destroy()
                self.callback((x1, y1, x2, y2))
            else:
                # 너무 작은 영역 선택 시 경고 없이 다시 선택하도록 함
                if self.rect_id:
                    self.canvas.delete(self.rect_id)
                self.start_x = None
                self.start_y = None
    
    def on_key_press(self, event):
        """키 입력 처리"""
        if event.keysym == 'Escape':
            self.cancel_selection()
    
    def cancel_selection(self, event=None):
        """선택 취소"""
        if self.selection_window:
            self.selection_window.destroy()
            self.callback(None)

class ScreenCaptureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("화면 캡쳐 프로그램")
        self.root.geometry("450x600")
        self.root.resizable(True, True)
        
        # 저장 폴더 설정 (기본값: 바탕화면)
        self.save_folder = os.path.expanduser("~/Desktop")
        
        # 파일명 prefix 설정
        self.filename_prefix = "screenshot"
        
        # 모니터 정보 가져오기
        self.monitors = self.get_monitor_info()
        
        # GUI 구성
        self.setup_gui()
    
    def get_monitor_info(self):
        """모니터 정보 가져오기"""
        monitors = []
        
        # 방법 1: Windows API 사용 (가장 정확)
        if WIN32_AVAILABLE:
            try:
                def enum_display_monitors():
                    monitors_info = []
                    
                    def monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
                        monitor_info = win32api.GetMonitorInfo(hMonitor)
                        work_area = monitor_info['Work']
                        monitor_area = monitor_info['Monitor']
                        
                        monitors_info.append({
                            'handle': hMonitor,
                            'x': monitor_area[0],
                            'y': monitor_area[1],
                            'width': monitor_area[2] - monitor_area[0],
                            'height': monitor_area[3] - monitor_area[1],
                            'is_primary': monitor_info['Flags'] == win32con.MONITORINFOF_PRIMARY
                        })
                        return True
                    
                    win32api.EnumDisplayMonitors(None, None, monitor_enum_proc, 0)
                    return monitors_info
                
                win_monitors = enum_display_monitors()
                print(f"Windows API로 감지된 모니터 수: {len(win_monitors)}")
                
                for i, mon in enumerate(win_monitors):
                    monitor_info = {
                        'index': i,
                        'name': f"모니터 {i+1}",
                        'x': mon['x'],
                        'y': mon['y'],
                        'width': mon['width'],
                        'height': mon['height'],
                        'is_primary': mon['is_primary'],
                        'handle': mon['handle']
                    }
                    monitors.append(monitor_info)
                    print(f"Windows API 모니터 {i+1}: {monitor_info}")
                    
            except Exception as e:
                print(f"Windows API로 모니터 정보 가져오기 실패: {e}")
        
        # 방법 2: screeninfo 라이브러리 사용
        if not monitors and SCREENINFO_AVAILABLE:
            try:
                import screeninfo
                screens = screeninfo.get_monitors()
                print(f"screeninfo로 감지된 모니터 수: {len(screens)}")
                
                for i, screen in enumerate(screens):
                    monitor_info = {
                        'index': i,
                        'name': f"모니터 {i+1}",
                        'x': screen.x,
                        'y': screen.y, 
                        'width': screen.width,
                        'height': screen.height,
                        'is_primary': screen.is_primary
                    }
                    monitors.append(monitor_info)
                    print(f"screeninfo 모니터 {i+1}: {monitor_info}")
                    
            except Exception as e:
                print(f"screeninfo로 모니터 정보 가져오기 실패: {e}")
        
        # 방법 3: Tkinter API 사용 (대안)
        if not monitors:
            try:
                import tkinter as tk
                temp_root = tk.Tk()
                temp_root.withdraw()
                
                # 주 모니터 정보
                screen_width = temp_root.winfo_screenwidth()
                screen_height = temp_root.winfo_screenheight()
                
                # 가상 화면 크기 (멀티 모니터 포함)
                virtual_width = temp_root.winfo_vrootwidth()
                virtual_height = temp_root.winfo_vrootheight()
                
                temp_root.destroy()
                
                print(f"주 모니터 크기: {screen_width}x{screen_height}")
                print(f"가상 화면 크기: {virtual_width}x{virtual_height}")
                
                # 주 모니터
                monitors.append({
                    'index': 0,
                    'name': "모니터 1 (주)",
                    'x': 0,
                    'y': 0,
                    'width': screen_width,
                    'height': screen_height,
                    'is_primary': True
                })
                
                # 듀얼 모니터 추정 (가상 화면이 주 모니터보다 큰 경우)
                if virtual_width > screen_width:
                    second_width = virtual_width - screen_width
                    monitors.append({
                        'index': 1,
                        'name': "모니터 2",
                        'x': screen_width,  # 오른쪽에 위치 추정
                        'y': 0,
                        'width': second_width,
                        'height': screen_height,
                        'is_primary': False
                    })
                    print(f"추정된 두 번째 모니터: ({screen_width}, 0) - {second_width}x{screen_height}")
                
            except Exception as e:
                print(f"Tkinter API 방식 실패: {e}")
        
        # 기본값 (모든 방법이 실패한 경우)
        if not monitors:
            try:
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                monitors.append({
                    'index': 0,
                    'name': "주 모니터",
                    'x': 0,
                    'y': 0,
                    'width': screen_width,
                    'height': screen_height,
                    'is_primary': True
                })
            except:
                # 최후의 수단
                monitors.append({
                    'index': 0,
                    'name': "기본 모니터",
                    'x': 0,
                    'y': 0,
                    'width': 1920,
                    'height': 1080,
                    'is_primary': True
                })
        
        print(f"최종 모니터 정보: {monitors}")
        return monitors

    def setup_gui(self):
        # 제목
        title_label = tk.Label(self.root, text="화면 캡쳐 프로그램", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # 저장 설정 프레임
        save_frame = tk.LabelFrame(self.root, text="저장 설정", font=("Arial", 10, "bold"))
        save_frame.pack(pady=10, padx=20, fill="x")
        
        # 저장 폴더 선택
        folder_frame = tk.Frame(save_frame)
        folder_frame.pack(pady=5, fill="x")
        
        tk.Label(folder_frame, text="저장 폴더:", font=("Arial", 9)).pack(anchor="w")
        
        folder_select_frame = tk.Frame(folder_frame)
        folder_select_frame.pack(fill="x", pady=2)
        
        self.folder_var = tk.StringVar(value=self.save_folder)
        folder_entry = tk.Entry(folder_select_frame, textvariable=self.folder_var, 
                               font=("Arial", 8), state="readonly")
        folder_entry.pack(side="left", fill="x", expand=True)
        
        folder_btn = tk.Button(folder_select_frame, text="찾아보기", 
                              command=self.select_save_folder,
                              font=("Arial", 8))
        folder_btn.pack(side="right", padx=(5, 0))
        
        # 파일명 prefix 설정
        prefix_frame = tk.Frame(save_frame)
        prefix_frame.pack(pady=5, fill="x")
        
        tk.Label(prefix_frame, text="파일명 접두사:", font=("Arial", 9)).pack(anchor="w")
        self.prefix_var = tk.StringVar(value=self.filename_prefix)
        prefix_entry = tk.Entry(prefix_frame, textvariable=self.prefix_var, font=("Arial", 9))
        prefix_entry.pack(fill="x", pady=2)
        
        # 파일 형식 선택
        format_frame = tk.Frame(save_frame)
        format_frame.pack(pady=5, fill="x")
        
        tk.Label(format_frame, text="파일 형식:", font=("Arial", 9)).pack(anchor="w")
        self.format_var = tk.StringVar(value="PNG")
        format_combo = ttk.Combobox(format_frame, textvariable=self.format_var, 
                                   values=["PNG", "JPEG", "BMP"], 
                                   state="readonly", font=("Arial", 9))
        format_combo.pack(fill="x", pady=2)
        
        # 캡쳐 버튼 프레임
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10, fill="x", padx=20)
        
        # 전체 화면 캡쳐 버튼
        full_screen_btn = tk.Button(button_frame, text="전체 화면 캡쳐", 
                                   command=self.capture_full_screen,
                                   bg="#4CAF50", fg="white", 
                                   font=("Arial", 10, "bold"),
                                   width=18, height=2)
        full_screen_btn.pack(pady=3, fill="x")
        
        # 모니터별 캡쳐 버튼들
        if len(self.monitors) > 1:
            monitor_frame = tk.LabelFrame(button_frame, text="개별 모니터 캡쳐", 
                                        font=("Arial", 9, "bold"))
            monitor_frame.pack(pady=5, fill="x")
            
            for monitor in self.monitors:
                monitor_text = f"{monitor['name']} ({monitor['width']}x{monitor['height']})"
                if monitor['is_primary']:
                    monitor_text += " [주]"
                
                monitor_btn = tk.Button(monitor_frame, text=monitor_text,
                                      command=lambda m=monitor: self.capture_monitor(m),
                                      bg="#607D8B", fg="white",
                                      font=("Arial", 9),
                                      width=18, height=1)
                monitor_btn.pack(pady=1, fill="x", padx=5)
        
        # 영역 선택 캡쳐 버튼
        region_btn = tk.Button(button_frame, text="영역 선택 캡쳐", 
                              command=self.capture_region,
                              bg="#2196F3", fg="white", 
                              font=("Arial", 10, "bold"),
                              width=18, height=2)
        region_btn.pack(pady=3, fill="x")
        
        # 좌표로 영역 캡쳐 버튼
        coord_region_btn = tk.Button(button_frame, text="좌표로 영역 캡쳐", 
                                    command=self.capture_region_by_coordinates,
                                    bg="#9C27B0", fg="white", 
                                    font=("Arial", 10),
                                    width=18, height=1)
        coord_region_btn.pack(pady=3, fill="x")
        
        # 저장 폴더 열기 버튼
        open_folder_btn = tk.Button(button_frame, text="저장 폴더 열기", 
                                   command=self.open_save_folder,
                                   bg="#FF9800", fg="white", 
                                   font=("Arial", 9),
                                   width=18, height=1)
        open_folder_btn.pack(pady=3, fill="x")
        
        # 구분선
        separator = tk.Frame(button_frame, height=1, bg="gray")
        separator.pack(fill="x", pady=5)
        
        # 모니터 정보 확인 버튼 (디버깅용)
        debug_btn = tk.Button(button_frame, text="🖥️ 모니터 정보 확인", 
                             command=self.show_monitor_info,
                             bg="#795548", fg="white", 
                             font=("Arial", 9, "bold"),
                             width=18, height=2)
        debug_btn.pack(pady=5, fill="x")

    def select_save_folder(self):
        """저장 폴더 선택"""
        folder = filedialog.askdirectory(
            title="캡쳐 파일을 저장할 폴더를 선택하세요",
            initialdir=self.save_folder
        )
        if folder:
            self.save_folder = folder
            self.folder_var.set(folder)
            messagebox.showinfo("알림", f"저장 폴더가 변경되었습니다:\n{folder}")
    
    def open_save_folder(self):
        """저장 폴더를 탐색기에서 열기"""
        try:
            if os.path.exists(self.save_folder):
                os.startfile(self.save_folder)  # Windows에서 폴더 열기
            else:
                messagebox.showerror("오류", "저장 폴더가 존재하지 않습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"폴더를 열 수 없습니다: {str(e)}")
    
    def generate_filename(self, capture_type="full"):
        """파일명 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = self.prefix_var.get() or "screenshot"
        file_format = self.format_var.get().lower()
        filename = f"{prefix}_{capture_type}_{timestamp}.{file_format}"
        return os.path.join(self.save_folder, filename)
    
    def capture_full_screen(self):
        """전체 화면 캡쳐"""
        try:
            # 저장 폴더 업데이트
            self.save_folder = self.folder_var.get()
            
            # 저장 폴더가 존재하는지 확인하고 없으면 생성
            if not os.path.exists(self.save_folder):
                os.makedirs(self.save_folder)
            
            # 잠시 창을 최소화
            self.root.withdraw()
            
            # 1초 대기 후 캡쳐
            self.root.after(1000, lambda: self._do_full_capture())
            
        except Exception as e:
            messagebox.showerror("오류", f"캡쳐 중 오류가 발생했습니다: {str(e)}")
            self.root.deiconify()
    
    def _do_full_capture(self):
        """실제 전체 화면 캡쳐 실행"""
        try:
            # 파일 경로 생성
            filepath = self.generate_filename("full")
            
            # 스크린샷 촬영
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            
            # 창 다시 표시
            self.root.deiconify()
            
            # 성공 메시지와 함께 파일 열기 옵션 제공
            result = messagebox.askyesno("완료", 
                                       f"스크린샷이 저장되었습니다:\n{filepath}\n\n파일을 열어보시겠습니까?")
            if result:
                os.startfile(filepath)
            
        except Exception as e:
            self.root.deiconify()
            messagebox.showerror("오류", f"캡쳐 중 오류가 발생했습니다: {str(e)}")
    
    def capture_region(self):
        """영역 선택 캡쳐"""
        try:
            # 저장 폴더 업데이트
            self.save_folder = self.folder_var.get()
            
            # 저장 폴더가 존재하는지 확인하고 없으면 생성
            if not os.path.exists(self.save_folder):
                os.makedirs(self.save_folder)
            
            # 잠시 창을 최소화
            self.root.withdraw()
            
            # 영역 선택 시작 (parent_root 전달)
            selector = RegionSelector(self.root, self._on_region_selected)
            # 500ms 후 영역 선택 창 표시
            self.root.after(500, selector.start_selection)
            
        except Exception as e:
            messagebox.showerror("오류", f"캡쳐 중 오류가 발생했습니다: {str(e)}")
            self.root.deiconify()
    
    def _on_region_selected(self, region):
        """영역 선택 완료 콜백"""
        try:
            if region is None:
                # 선택 취소됨
                self.root.deiconify()
                return
            
            x1, y1, x2, y2 = region
            
            # 파일 경로 생성
            filepath = self.generate_filename("region")
            
            # 선택된 영역의 크기 계산
            width = x2 - x1
            height = y2 - y1
            
            print(f"선택된 영역: ({x1}, {y1}) - ({x2}, {y2}), 크기: {width}x{height}")
            
            # 선택된 영역 캡쳐
            screenshot = pyautogui.screenshot(region=(x1, y1, width, height))
            screenshot.save(filepath)
            
            # 창 다시 표시
            self.root.deiconify()
            
            # 성공 메시지와 함께 파일 열기 옵션 제공
            result = messagebox.askyesno("완료", 
                                       f"영역 스크린샷이 저장되었습니다:\n"
                                       f"파일: {filepath}\n"
                                       f"크기: {width}x{height}\n\n"
                                       f"파일을 열어보시겠습니까?")
            if result:
                os.startfile(filepath)
            
        except Exception as e:
            self.root.deiconify()
            messagebox.showerror("오류", f"영역 캡쳐 중 오류가 발생했습니다: {str(e)}")
    
    def capture_region_by_coordinates(self):
        """좌표 입력으로 영역 캡쳐"""
        try:
            # 좌표 입력 창 생성
            coord_window = tk.Toplevel(self.root)
            coord_window.title("영역 좌표 입력")
            coord_window.geometry("400x300")
            coord_window.resizable(False, False)
            coord_window.grab_set()
            
            # 전체 화면 크기 정보 표시
            total_width = sum(m['width'] for m in self.monitors)
            max_height = max(m['height'] for m in self.monitors)
            
            info_frame = tk.Frame(coord_window)
            info_frame.pack(pady=5, padx=10, fill="x")
            
            tk.Label(info_frame, text="모니터 정보:", font=("Arial", 10, "bold")).pack(anchor="w")
            
            for monitor in self.monitors:
                monitor_info = (f"{monitor['name']}: "
                              f"({monitor['x']}, {monitor['y']}) - "
                              f"({monitor['x'] + monitor['width']}, {monitor['y'] + monitor['height']}) "
                              f"[{monitor['width']}x{monitor['height']}]")
                tk.Label(info_frame, text=monitor_info, font=("Arial", 8)).pack(anchor="w", padx=10)
            
            tk.Label(info_frame, text=f"전체 영역: {total_width}x{max_height}", 
                    font=("Arial", 9, "bold")).pack(anchor="w", pady=(5,0))
            
            # 좌표 입력 프레임
            coord_frame = tk.Frame(coord_window)
            coord_frame.pack(pady=10, padx=20, fill="x")
            
            # X1, Y1 (시작점)
            start_frame = tk.Frame(coord_frame)
            start_frame.pack(fill="x", pady=5)
            tk.Label(start_frame, text="시작점 (X1, Y1):", width=15, anchor="w").pack(side="left")
            x1_var = tk.StringVar(value="100")
            y1_var = tk.StringVar(value="100")
            tk.Entry(start_frame, textvariable=x1_var, width=8).pack(side="left", padx=2)
            tk.Label(start_frame, text=",").pack(side="left")
            tk.Entry(start_frame, textvariable=y1_var, width=8).pack(side="left", padx=2)
            
            # X2, Y2 (끝점)
            end_frame = tk.Frame(coord_frame)
            end_frame.pack(fill="x", pady=5)
            tk.Label(end_frame, text="끝점 (X2, Y2):", width=15, anchor="w").pack(side="left")
            x2_var = tk.StringVar(value="500")
            y2_var = tk.StringVar(value="400")
            tk.Entry(end_frame, textvariable=x2_var, width=8).pack(side="left", padx=2)
            tk.Label(end_frame, text=",").pack(side="left")
            tk.Entry(end_frame, textvariable=y2_var, width=8).pack(side="left", padx=2)
            
            def capture_by_coords():
                try:
                    x1 = int(x1_var.get())
                    y1 = int(y1_var.get())
                    x2 = int(x2_var.get())
                    y2 = int(y2_var.get())
                    
                    # 좌표 정렬
                    if x1 > x2:
                        x1, x2 = x2, x1
                    if y1 > y2:
                        y1, y2 = y2, y1
                    
                    # 범위 체크 (모든 모니터 영역 고려)
                    min_x = min(m['x'] for m in self.monitors)
                    min_y = min(m['y'] for m in self.monitors)
                    max_x = max(m['x'] + m['width'] for m in self.monitors)
                    max_y = max(m['y'] + m['height'] for m in self.monitors)
                    
                    if x1 < min_x or y1 < min_y or x2 > max_x or y2 > max_y:
                        messagebox.showerror("오류", 
                                           f"좌표가 모니터 범위를 벗어났습니다.\n"
                                           f"유효 범위: ({min_x}, {min_y}) - ({max_x}, {max_y})")
                        return
                    
                    if x2 - x1 < 10 or y2 - y1 < 10:
                        messagebox.showerror("오류", "캡쳐 영역이 너무 작습니다.")
                        return
                    
                    coord_window.destroy()
                    
                    # 캡쳐 실행
                    self._capture_region_by_coords(x1, y1, x2, y2)
                    
                except ValueError:
                    messagebox.showerror("오류", "올바른 숫자를 입력해주세요.")
            
            # 버튼 프레임
            btn_frame = tk.Frame(coord_window)
            btn_frame.pack(pady=10)
            
            tk.Button(btn_frame, text="캡쳐", command=capture_by_coords,
                     bg="#4CAF50", fg="white", width=10).pack(side="left", padx=5)
            tk.Button(btn_frame, text="취소", command=coord_window.destroy,
                     bg="#f44336", fg="white", width=10).pack(side="left", padx=5)
            
        except Exception as e:
            messagebox.showerror("오류", f"좌표 입력 창 생성 중 오류: {str(e)}")
    
    def _capture_region_by_coords(self, x1, y1, x2, y2):
        """좌표로 영역 캡쳐 실행"""
        try:
            # 저장 폴더 업데이트
            self.save_folder = self.folder_var.get()
            
            # 저장 폴더가 존재하는지 확인하고 없으면 생성
            if not os.path.exists(self.save_folder):
                os.makedirs(self.save_folder)
            
            # 파일 경로 생성
            filepath = self.generate_filename("coords")
            
            width = x2 - x1
            height = y2 - y1
            
            # 영역 캡쳐
            screenshot = pyautogui.screenshot(region=(x1, y1, width, height))
            screenshot.save(filepath)
            
            # 성공 메시지
            result = messagebox.askyesno("완료", 
                                       f"좌표 영역 스크린샷이 저장되었습니다:\n"
                                       f"파일: {filepath}\n"
                                       f"영역: ({x1}, {y1}) - ({x2}, {y2})\n"
                                       f"크기: {width}x{height}\n\n"
                                       f"파일을 열어보시겠습니까?")
            if result:
                os.startfile(filepath)
            
        except Exception as e:
            messagebox.showerror("오류", f"좌표 캡쳐 중 오류가 발생했습니다: {str(e)}")
    
    def capture_monitor(self, monitor):
        """특정 모니터 캡쳐"""
        try:
            # 저장 폴더 업데이트
            self.save_folder = self.folder_var.get()
            
            # 저장 폴더가 존재하는지 확인하고 없으면 생성
            if not os.path.exists(self.save_folder):
                os.makedirs(self.save_folder)
            
            # 잠시 창을 최소화
            self.root.withdraw()
            
            # 1초 대기 후 캡쳐
            self.root.after(1000, lambda: self._do_monitor_capture(monitor))
            
        except Exception as e:
            messagebox.showerror("오류", f"모니터 캡쳐 중 오류가 발생했습니다: {str(e)}")
            self.root.deiconify()
    
    def _do_monitor_capture(self, monitor):
        try:
            filepath = self.generate_filename(f"monitor_{monitor['index']+1}")

            # 1. BitBlt 방식 (가장 정확)
            if WIN32_AVAILABLE and 'handle' in monitor:
                try:
                    import win32gui
                    import win32ui
                    import win32con
                    import win32api
                    from PIL import Image

                    monitor_info = win32api.GetMonitorInfo(monitor['handle'])
                    monitor_rect = monitor_info['Monitor']

                    hwnd = win32gui.GetDesktopWindow()
                    hwindc = win32gui.GetWindowDC(hwnd)
                    srcdc = win32ui.CreateDCFromHandle(hwindc)
                    memdc = srcdc.CreateCompatibleDC()

                    width = monitor_rect[2] - monitor_rect[0]
                    height = monitor_rect[3] - monitor_rect[1]
                    print(f"BitBlt 좌표: {monitor_rect}, width: {width}, height: {height}")
                    bmp = win32ui.CreateBitmap()
                    bmp.CreateCompatibleBitmap(srcdc, width, height)
                    memdc.SelectObject(bmp)

                    result = memdc.BitBlt((0, 0), (width, height), srcdc, (monitor_rect[0], monitor_rect[1]), win32con.SRCCOPY)

                    if result:
                        bmpinfo = bmp.GetInfo()
                        bmpstr = bmp.GetBitmapBits(True)
                        img = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                                              bmpstr, 'raw', 'BGRX', 0, 1)
                        img.save(filepath)
                        actual_size = img.size
                        self.root.deiconify()
                        result = messagebox.askyesno("완료", 
                            f"{monitor['name']} 스크린샷이 저장되었습니다:\n"
                            f"파일: {filepath}\n"
                            f"크기: {actual_size[0]}x{actual_size[1]}\n"
                            f"좌표: ({monitor['x']}, {monitor['y']})\n\n"
                            f"파일을 열어보시겠습니까?")
                        if result:
                            os.startfile(filepath)
                        # 리소스 해제
                        memdc.DeleteDC()
                        srcdc.DeleteDC()
                        win32gui.ReleaseDC(hwnd, hwindc)
                        win32gui.DeleteObject(bmp.GetHandle())
                        return
                    else:
                        print("BitBlt 실패")
                        memdc.DeleteDC()
                        srcdc.DeleteDC()
                        win32gui.ReleaseDC(hwnd, hwindc)
                        win32gui.DeleteObject(bmp.GetHandle())
                except Exception as api_error:
                    print(f"Windows API BitBlt 방식 실패: {api_error}")
                    messagebox.showerror("실패", f"{monitor['name']} 캡쳐에 BitBlt 예외 발생:\n{api_error}")
                    self.root.deiconify()
                    return

            # 2. BitBlt가 실패하면 PIL ImageGrab fallback
            try:
                from PIL import ImageGrab
                all_monitors = self.monitors
                min_x = min(m['x'] for m in all_monitors)
                min_y = min(m['y'] for m in all_monitors)
                max_x = max(m['x'] + m['width'] for m in all_monitors)
                max_y = max(m['y'] + m['height'] for m in all_monitors)

                full_screenshot = ImageGrab.grab(all_screens=True)
                img_width, img_height = full_screenshot.size
                expected_width = max_x - min_x
                expected_height = max_y - min_y

                print(f"ImageGrab size: {img_width}x{img_height}, expected: {expected_width}x{expected_height}")

                crop_left = monitor['x'] - min_x
                crop_top = monitor['y'] - min_y
                crop_right = crop_left + monitor['width']
                crop_bottom = crop_top + monitor['height']

                box = (crop_left, crop_top, crop_right, crop_bottom)
                monitor_screenshot = full_screenshot.crop(box)
                monitor_screenshot.save(filepath)
                actual_size = monitor_screenshot.size

                self.root.deiconify()
                result = messagebox.askyesno("완료", 
                    f"{monitor['name']} 스크린샷이 저장되었습니다:\n"
                    f"파일: {filepath}\n"
                    f"크기: {actual_size[0]}x{actual_size[1]}\n"
                    f"좌표: ({monitor['x']}, {monitor['y']})\n\n"
                    f"파일을 열어보시겠습니까?")
                if result:
                    os.startfile(filepath)
                return
            except Exception as e:
                print(f"ImageGrab fallback 실패: {e}")
                messagebox.showerror("실패", f"{monitor['name']} 캡쳐에 실패했습니다. (BitBlt & ImageGrab 실패)\n{e}")
                self.root.deiconify()
                return

        except Exception as e:
            self.root.deiconify()
            print(f"모니터 캡쳐 전체 오류: {e}")
            messagebox.showerror("오류", f"모니터 캡쳐 중 오류가 발생했습니다: {str(e)}")

    def show_monitor_info(self):
        """모니터 정보를 팝업으로 표시"""
        info_text = "현재 감지된 모니터 정보:\n\n"
        
        for monitor in self.monitors:
            info_text += f"{monitor['name']}:\n"
            info_text += f"  위치: ({monitor['x']}, {monitor['y']})\n"
            info_text += f"  크기: {monitor['width']} x {monitor['height']}\n"
            info_text += f"  주 모니터: {'예' if monitor['is_primary'] else '아니오'}\n"
            info_text += f"  영역: ({monitor['x']}, {monitor['y']}) - "
            info_text += f"({monitor['x'] + monitor['width']}, {monitor['y'] + monitor['height']})\n\n"
        
        # 전체 화면 정보
        try:
            virtual_width = self.root.winfo_vrootwidth()
            virtual_height = self.root.winfo_vrootheight()
            info_text += f"가상 화면 크기: {virtual_width} x {virtual_height}\n"
        except:
            pass
        
        messagebox.showinfo("모니터 정보", info_text)

def main():
    # pyautogui 설정
    pyautogui.FAILSAFE = True  # 마우스를 화면 모서리로 이동하면 중단
    
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception as dpi_error:
        print(f"DPI aware 설정 실패: {dpi_error}")
    
    # GUI 애플리케이션 실행
    root = tk.Tk()
    app = ScreenCaptureApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()