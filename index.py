from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

class BooksScraper:
    """Scrape books details from ZLibrary website (https://singlelogin.re/)
    """

    def __init__(self, search_keyword):
        """Create instance variables 
        Args:
            search_keyword (str): Search keyword, can be title, author, ISBN, publisher
        """
        self.search_keyword = search_keyword.replace(' ', '%20')
        self.page = 1
        self.search_link = f'https://singlelogin.re/s/{self.search_keyword}?page={self.page}'
        print(f"Searching for: {self.search_keyword}")

    def get_books_urls_and_details(self):
        """Get books URLs and details from all pages and return them as a list of dictionaries
        Returns:
            list: A list of dictionaries containing book details
        """
        books = []
        max_books = 15  # Limit to 15 books

        while len(books) < max_books:
            # Get books URLs in the current page
            print(f"Fetching page: {self.page}")
            page_html = requests.get(self.search_link).text
            page_parsed_html = BeautifulSoup(page_html, 'lxml')

            book_elements = page_parsed_html.find_all('table', {'class': 'resItemTable'})
            if not book_elements:
                print("No books found on this page.")
                break

            for book_element in book_elements:
                if len(books) >= max_books:
                    break  # Exit if we have reached the limit

                try:
                    book_url = 'https://singlelogin.re' + book_element.h3.a['href']
                    book_title = book_element.h3.a.text.strip()
                    print(f"Found book: {book_title}")

                    # Scrape book details from the book page
                    book_page_html = requests.get(book_url).text
                    book_page_parsed_html = BeautifulSoup(book_page_html, 'lxml')

                    main_div = book_page_parsed_html.find('div', {'class': 'col-sm-9'})
                    if not main_div:
                        continue

                    # Collect book details
                    book_details = {
                        'title': book_title,
                        'url': book_url,
                        'author(s)': self.get_text_or_none(main_div, 'bookProperty property_authors', 'author'),
                        'year': self.get_text_or_none(main_div, 'bookProperty property_year'),
                        'edition': self.get_text_or_none(main_div, 'bookProperty property_edition'),
                        'publisher': self.get_text_or_none(main_div, 'bookProperty property_publisher'),
                        'language': self.get_text_or_none(main_div, 'bookProperty property_language'),
                        'pages': self.get_text_or_none(main_div, 'bookProperty property_pages'),
                        'category(s)': self.get_text_or_none(main_div, 'bookProperty property_categories'),
                        'ISBN_13': self.get_text_or_none(main_div, 'bookProperty property_isbn 13'),
                        'rating(5)': self.get_rating_or_none(main_div),
                        'reader_link': self.get_reader_link(book_page_parsed_html)
                    }
                    books.append(book_details)

                except Exception as e:
                    print(f"Error processing book: {e}")
                    continue

            # Move to the next page
            next_page_element = page_parsed_html.find('div', {'class': 'paginator'})
            if not next_page_element or not next_page_element.a:
                print("No more pages.")
                break
            next_page_num = next_page_element.a['href'].split('?')[-1].split('=')[-1]
            self.page = int(next_page_num)
            self.search_link = f'https://singlelogin.re/s/{self.search_keyword}?page={self.page}'

        return books

    @staticmethod
    def get_text_or_none(div, class_name, itemprop=None):
        """Get text from a div with specific class name and itemprop attribute
        Args:
            div (BeautifulSoup): The BeautifulSoup div element
            class_name (str): The class name to find
            itemprop (str): The itemprop attribute to find (optional)
        Returns:
            str: The text if found, otherwise None
        """
        try:
            property_div = div.find('div', {'class': class_name})
            if itemprop:
                property_div = property_div.find('a', {'itemprop': itemprop})
            else:
                property_div = property_div.find('div', {'class': 'property_value'})
            return property_div.text.strip()
        except Exception:
            return None

    @staticmethod
    def get_rating_or_none(div):
        """Get rating from a div
        Args:
            div (BeautifulSoup): The BeautifulSoup div element
        Returns:
            float: The rating if found, otherwise None
        """
        try:
            rating_span = div.find('span', {'class': 'book-rating-interest-score'})
            if not rating_span:
                rating_span = div.find('span', {'class': 'book-rating-interest-score none'})
            return float(rating_span.text)
        except Exception:
            return None

    @staticmethod
    def get_reader_link(parsed_html):
        """Get the reader link from the book page
        Args:
            parsed_html (BeautifulSoup): The BeautifulSoup parsed HTML of the book page
        Returns:
            str: The reader link if found, otherwise None
        """
        try:
            reader_link = parsed_html.find('a', {'class': 'reader-link'})
            return 'https://reader2.z-library.sk' + reader_link['href']
        except Exception:
            return None

@app.route('/search', methods=['GET'])
def search_books():
    """API endpoint to search for books and return the details in JSON format
    Returns:
        JSON: List of books with their details
    """
    search_keyword = request.args.get('nome', '')
    if not search_keyword:
        return jsonify({'error': 'Parâmetro "nome" é necessário.'}), 400

    scraper = BooksScraper(search_keyword)
    books = scraper.get_books_urls_and_details()

    if not books:
        return jsonify({'message': 'Nenhum livro encontrado.'}), 404

    return jsonify(books)

if __name__ == '__main__':
    app.run(debug=False)
