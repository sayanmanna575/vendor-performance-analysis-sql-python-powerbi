import sqlite3
import pandas as pd
import loggin
from ingestion_db import ingest_db

loggin.basicConfig(
    filename = "logs/get_vendor_summary.log",
    level = loggin.DEBUG,
    format = "%(asctime)s - %(levelname)s - %(message)s",
    filemode = "a"
)

def create_vendor_summary(conn):
    '''this function will merge the different tables to get the overall vendor summary and adding new columns in the resultant data'''
    vendor_sales_summary = pd.read_sql_query("""WITH FreightSummary AS(
        SELECT
            VendorNumber, 
            SUM(Freight) as FreightCost
        From vendor_invoice
        Group BY VendorNumber    
    ),
    PurchaseSummary AS(
        SELECT 
            p.VendorNumber,
            p.VendorName,
            p.Brand,
            p.Description,
            p.PurchasePrice,
            pp.price as ActualPrice,
            pp.Volume,
            SUM(p.Quantity) as TotalPurchaseQuantity,
            SUM(p.Dollars) as TotalPurchaseDollars
        FROM purchases p
        JOIN purchase_prices pp 
        on p.Brand = pp.Brand
        where p.PurchasePrice>0
        GROUP BY p.VendorNumber, p.VendorName, p.Brand,p.Description, p.PurchasePrice, pp.Volume
    ),
    SalesSummary AS (
        SELECT
            VendorNo,
            Brand,
            SUM(SalesQuantity) as TotalSalesQuantity,
            SUM(SalesDollars) as TotalSalesDollars,
            SUM(SalesPrice) as TotalSalesPrice,
            SUM(ExciseTax) as TotalExciseTax
        FROM sales
        GROUP BY VendorNo, Brand
    )
    SELECT
        ps.VendorNumber,
        ps.VendorName,
        ps.Brand,
        ps.Description,
        ps.PurchasePrice,
        ps.ActualPrice,
        ps.Volume,
        ps.TotalPurchaseQuantity,
        ps.TotalPurchaseDollars,
        ss.TotalSalesQuantity,
        ss.TotalSalesDollars,
        ss.TotalSalesPrice,
        ss.TotalExciseTax,
        fs.FreightCost
    FROM purchaseSummary ps
    LEFT JOIN salesSummary ss
    ON ps.VendorNumber = ss.VendorNo
    AND ps.Brand = ss.Brand
    LEFT JOIN FreightSummary fs
    ON ps.VendorNumber = fs.VendorNumber
    ORDER BY ps.TotalPurchaseDollars DESC""",conn)
    
    return vendor_sales_summary


def clean_data(df):
    '''this function will clean the data'''
    #changing datatype to float
    df['Volume']= df['Volume'].astype('float')

    #filling missing value with 0
    df.fillna(0,inplace = True)

    #removing spaces from categorical columns
    df['VendorName'] = df['VendorName'].str.strip()
    df['Description'] = df['Description'].str.strip()

    #creating new columns for better analysis
     vendor_sales_summary['GrossProfit'] =  vendor_sales_summary['TotalSalesDollars'] - vendor_sales_summary['TotalPurchaseDollars']
    vendor_sales_summary['ProfitMergin'] = (vendor_sales_summary['GrossProfit'] / vendor_sales_summary['TotalSalesDollars'])*100
    vendor_sales_summary['StockTurnover'] = vendor_sales_summary['TotalSalesQuantity'] / vendor_sales_summary['TotalPurchaseQuantity']
    vendor_sales_summary['SalestoPurchaseRatio'] = vendor_sales_summary['TotalSalesDollars']/ vendor_sales_summary['TotalPurchaseDollars']

    return df

if__name__=='__main__':
    #creating database connection
    conn = sqllite3.connect('inventory.db')

    loggin.info('Creating vendor Summary Table......')
    summary_df = create_vendor_summary(conn)
    loggin.info(summary_df.head())

    loggin.info('Cleaning Data......')
    clean_df = clean_data(summary_df)
    loggin.info(clean_df.head())

    loggin.info('Inserting Data......')
    ingest_db(clean_df,'vendor_sales_summary',conn)
    loggin.info('Completed')
