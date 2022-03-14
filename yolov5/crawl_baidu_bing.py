import os
from icrawler.builtin import BaiduImageCrawler
from icrawler.builtin import BingImageCrawler

def check_path(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def baidu_bing_crwal(key_words=['搞笑图片'], max_nums=[1000], save_root=r'./'):

    assert len(key_words)==len(max_nums), "关键词和数量必须一致"
    # # 2个一起爬虫
    # save_root1 = os.path.join(save_root, 'baidu')
    # # 百度爬虫
    # for i in range(len(key_words)):
    #     print('-'*20)
    #     image_save_root = os.path.join(save_root1, str(i))
    #
    #     if not os.path.exists(image_save_root):
    #         os.makedirs(image_save_root)
    #
    #     storage = {'root_dir': image_save_root}
    #     crawler = BaiduImageCrawler(storage=storage)
    #     crawler.crawl(key_words[i], max_num=max_nums[i])

    # bing爬虫
    save_root2 = os.path.join(save_root, 'bing')
    for i in range(len(key_words)):
        print('-'*20)
        image_save_root = os.path.join(save_root2, str(i))

        if not os.path.exists(image_save_root):
            os.makedirs(image_save_root)

        storage = {'root_dir': image_save_root}
        crawler = BingImageCrawler(storage=storage)

        crawler.crawl(key_words[i], max_num=max_nums[i])
    return

if __name__ == '__main__':
    baidu_bing_crwal(key_words=['键盘','鼠标'],
                     max_nums=[100,100],
                     save_root=r'/home/px/Desktop/lyf/tensorrtx/yolov5/samples')