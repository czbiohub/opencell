import React, {Component} from 'react';
import {cellLineMetadataDefinitions} from './metadataDefinitions.js';
import { MetadataContainer } from './common.jsx';


class Header extends Component {

    constructor (props) {
        super(props);

        // metadata items to display in the header
        const metadataDefinitionIds = [
            'protein_name', 
            'target_terminus', 
            'uniprot_id', 
            'plate_id', 
            'well_id', 
            'hdr_all', 
            'hdr_modified', 
            'facs_grade'
        ];

        this.definitions = cellLineMetadataDefinitions.filter(
            def => metadataDefinitionIds.includes(def.id)
        );

    }


    render () {

        return (

            <div className="flex items-center w-100 pt3 pb3 header-container">

                {/* OpenCell graphic logo */}
                <div>
                    <img src='./logos/opencell_logo.png' width={90} height={90}/>
                </div>

                {/* 'OpenCell' text header on top of the CZB logo */}
                <div className='pl3'>
                    <div className="pb1 blue header-opencell-title">{'OpenCell'}</div>
                    <img src='./logos/logo_text_smaller.png' width={100}/>
                </div>
                
                {/* target name */}
                <div className="pl4 blue header-target-name">
                    {this.props.cellLine.metadata?.target_name}
                </div>

                {/* target metadata items */}
                <div className='pl4'>
                    <MetadataContainer
                        className='items-center'
                        data={this.props.cellLine}
                        definitions={this.definitions}
                        orientation='row'
                        scale={3}
                    />
                </div>

                {/* target search box */}
                <div>
                    <input 
                        type='text' 
                        className='header-search-textbox' 
                        defaultValue={''}
                        onKeyPress={(event) => {
                            if (event.charCode===13) {
                                this.props.onSearchChange(event.currentTarget.value);
                            }
                        }}/>
                    <div className='f6 header-search-label'>Search by target name</div>
                </div>

            </div>

        );
    }
}



export default Header;