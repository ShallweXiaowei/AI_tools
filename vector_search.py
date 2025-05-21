import faiss
import numpy as np

# 加载向量数据
embeddings = np.load("my_text/email_vectors.npy")

# 加载 FAISS 索引
index = faiss.read_index("my_text/email_index.faiss")




import json

with open("my_text/recent_emails.json", "r", encoding="utf-8") as f:
    emails = json.load(f)



from sentence_transformers import SentenceTransformer

# 加载模型
model = SentenceTransformer("all-MiniLM-L6-v2")

def search_emails(query_text, top_k=5):
    # 将查询文本转换为向量
    query_vector = model.encode([query_text])
    
    # 在索引中搜索最相似的向量
    distances, indices = index.search(query_vector, top_k)
    
    # 打印搜索结果
    for idx in indices[0]:
        email = emails[idx]
        print(f"Subject: {email['subject']}")
        print(f"From: {email['from']}")
        print(f"Date: {email['date']}")
        print(f"Body:\n{email['body'][:300]}...\n")
        print("="*60)

if __name__=="__main__":
    # 示例查询
    search_emails("university of rochester", top_k=5)
    # 你可以修改查询文本和 top_k 值来进行不同的搜索