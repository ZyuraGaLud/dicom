import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import pydicom
from PIL import Image, ImageTk

class FinalDICOMViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("知能情報実験実習2 - 医用画像Viewer (3断面スライダー版)")
        self.root.geometry("1250x900")

        # データ管理
        self.volume = None
        self.cur_z = 0 # Axial用
        self.cur_x = 0 # Sagittal用
        self.cur_y = 0 # Coronal用
        self.ww = 2000 
        self.wl = 500  

        self.setup_ui()

    def setup_ui(self):
        # メインコンテナ
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左側：画像表示 (Axial, Sagittal, Coronal)
        left_frame = tk.Frame(main_container)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvases = {}
        #  Axial(原画像)は必ず表示
        views = [("Axial (Original)", 0, 0, "ax"), 
                 ("Sagittal", 0, 1, "sag"), 
                 ("Coronal", 1, 0, "cor")]
        
        for title, r, c, key in views:
            f = tk.Frame(left_frame)
            f.grid(row=r, column=c, padx=5, pady=5)
            tk.Label(f, text=title, font=("Arial", 10, "bold")).pack()
            cv = tk.Canvas(f, width=380, height=380, bg="black", highlightthickness=1)
            cv.pack()
            self.canvases[key] = cv

        # 右側：操作パネル
        right_frame = tk.Frame(main_container, width=350, padx=20)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # 読み込みボタン [cite: 19, 20]
        self.btn_load = tk.Button(right_frame, text="DICOMフォルダを選択", command=self.load_folder, 
                                 height=2, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.btn_load.pack(fill=tk.X, pady=(0, 15))

        # DICOMヘッダ情報 [cite: 104, 105, 106, 107]
        info_box = tk.LabelFrame(right_frame, text="DICOMヘッダ情報", padx=10, pady=10)
        info_box.pack(fill=tk.X, pady=(0, 15))
        self.lbl_info = tk.Label(info_box, text="未読み込み", justify=tk.LEFT, font=("Arial", 9))
        self.lbl_info.pack(anchor="w")

        # --- スライス位置スライダー (3断面独立)  ---
        pos_box = tk.LabelFrame(right_frame, text="スライス位置変更", padx=10, pady=10)
        pos_box.pack(fill=tk.X, pady=(0, 15))

        tk.Label(pos_box, text="Axial 位置 (Z)").pack(anchor="w")
        self.slider_z = tk.Scale(pos_box, from_=0, to=100, orient=tk.HORIZONTAL, command=lambda e: self.update_view())
        self.slider_z.pack(fill=tk.X, pady=(0, 10))

        tk.Label(pos_box, text="Sagittal 位置 (X)").pack(anchor="w")
        self.slider_x = tk.Scale(pos_box, from_=0, to=100, orient=tk.HORIZONTAL, command=lambda e: self.update_view())
        self.slider_x.pack(fill=tk.X, pady=(0, 10))

        tk.Label(pos_box, text="Coronal 位置 (Y)").pack(anchor="w")
        self.slider_y = tk.Scale(pos_box, from_=0, to=100, orient=tk.HORIZONTAL, command=lambda e: self.update_view())
        self.slider_y.pack(fill=tk.X)

        # --- 階調調整スライダー  ---
        ww_box = tk.LabelFrame(right_frame, text="階調調整 (Windowing)", padx=10, pady=10)
        ww_box.pack(fill=tk.X)

        tk.Label(ww_box, text="Window Width (WW)").pack(anchor="w")
        self.slider_ww = tk.Scale(ww_box, from_=1, to=4000, orient=tk.HORIZONTAL, command=lambda e: self.update_view())
        self.slider_ww.set(2000)
        self.slider_ww.pack(fill=tk.X, pady=(0, 10))

        tk.Label(ww_box, text="Window Level (WL)").pack(anchor="w")
        self.slider_wl = tk.Scale(ww_box, from_=-1000, to=2000, orient=tk.HORIZONTAL, command=lambda e: self.update_view())
        self.slider_wl.set(500)
        self.slider_wl.pack(fill=tk.X)

    def load_folder(self):
        folder = filedialog.askdirectory()
        if not folder: return

        dcm_files = []
        for f in os.listdir(folder):
            if f.lower().endswith(".dcm"):
                try:
                    ds = pydicom.dcmread(os.path.join(folder, f))
                    if hasattr(ds, 'ImagePositionPatient'):
                        dcm_files.append(ds)
                except: continue

        if not dcm_files:
            messagebox.showwarning("警告", "DICOMファイルが見つかりません。")
            return

        # スライス順にソート [cite: 21]
        dcm_files.sort(key=lambda x: float(x.ImagePositionPatient[2]))
        
        volume_list = []
        for ds in dcm_files:
            pixel = ds.pixel_array.astype(np.float32)
            slope = float(getattr(ds, 'RescaleSlope', 1))
            intercept = float(getattr(ds, 'RescaleIntercept', 0))
            volume_list.append(pixel * slope + intercept)
        self.volume = np.stack(volume_list)

        # ヘッダ情報の更新表示 [cite: 105, 106, 107]
        ds = dcm_files[0]
        self.lbl_info.config(text=f"サイズ: {ds.Rows}x{ds.Columns}\n厚み: {getattr(ds, 'SliceThickness', 'N/A')}mm\nスライス数: {len(dcm_files)}")
        
        # スライダの範囲更新
        self.slider_z.config(to=self.volume.shape[0]-1) # Z枚数
        self.slider_y.config(to=self.volume.shape[1]-1) # Y行数
        self.slider_x.config(to=self.volume.shape[2]-1) # X列数

        # 初期位置を中央に設定
        self.slider_z.set(self.volume.shape[0]//2)
        self.slider_y.set(self.volume.shape[1]//2)
        self.slider_x.set(self.volume.shape[2]//2)
        
        self.update_view()

    def update_view(self):
        if self.volume is None: return
        self.cur_z = int(self.slider_z.get())
        self.cur_y = int(self.slider_y.get())
        self.cur_x = int(self.slider_x.get())
        self.ww = int(self.slider_ww.get())
        self.wl = int(self.slider_wl.get())

        # 指定されたインデックスでスライスを抽出
        ax = self.volume[self.cur_z, :, :]
        sag = self.volume[:, :, self.cur_x]
        cor = self.volume[:, self.cur_y, :]

        # 描画処理 [cite: 90, 93, 94]
        self.draw("ax", ax, is_ax=True)
        self.draw("sag", sag)
        self.draw("cor", cor)

    def draw(self, key, img_array, is_ax=False):
        # 階調変換 
        lower, upper = self.wl - self.ww//2, self.wl + self.ww//2
        img_adj = np.clip(((np.clip(img_array, lower, upper) - lower) / self.ww * 255), 0, 255).astype(np.uint8)

        # SagittalとCoronalは縦横比が変わる場合があるためリサイズ
        img_pil = Image.fromarray(img_adj).resize((380, 380), Image.LANCZOS)
        img_tk = ImageTk.PhotoImage(img_pil)
        
        cv = self.canvases[key]
        cv.image = img_tk
        cv.delete("all")
        cv.create_image(0, 0, anchor=tk.NW, image=img_tk)

        #  スライス番号を表示する
        slice_num = self.cur_z if is_ax else (self.cur_x if key=="sag" else self.cur_y)
        cv.create_text(15, 15, anchor=tk.NW, text=f"Slice: {slice_num}", fill="yellow", font=("Arial", 11, "bold"))

if __name__ == "__main__":
    root = tk.Tk()
    FinalDICOMViewer(root)
    root.mainloop()